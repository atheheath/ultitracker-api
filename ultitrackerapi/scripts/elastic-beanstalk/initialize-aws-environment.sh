#!/bin/bash
LETSENCRYPTFOLDER=$1

if [[ "${LETSENCRYPTFOLDER}" == "" ]]
then
    echo "Pass letsencrypt folder path as first argument"
fi 

VPCRESULT=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16)

VPCID=$(echo ${VPCRESULT} | jq -r '.Vpc.VpcId')

aws ec2 modify-vpc-attribute \
    --vpc-id ${VPCID} \
    --enable-dns-hostnames

IGRESULT=$(aws ec2 create-internet-gateway)
IGID=$(echo ${IGRESULT} | jq -r '.InternetGateway.InternetGatewayId')

aws ec2 attach-internet-gateway \
    --internet-gateway-id ${IGID} \
    --vpc-id ${VPCID}

ROUTETABLERESULT=$(aws ec2 create-route-table --vpc-id "${VPCID}")
ROUTETABLEID=$(echo ${ROUTETABLERESULT} | jq -r '.RouteTable.RouteTableId')

CREATEROUTERESULT=$(aws ec2 create-route \
    --route-table-id ${ROUTETABLEID} \
    --destination-cidr-block 0.0.0.0/0 \
    --gateway-id ${IGID})

SGRESULT=$(aws ec2 create-security-group \
    --vpc-id ${VPCID} \
    --group-name "ultitracker-api-eb-instances" \
    --description "Security group for ultitracker-api eb instances")

SGID=$(echo ${SGRESULT} | jq -r '.GroupId')

# postgres connections across security group
aws ec2 authorize-security-group-ingress \
    --group-id ${SGID} \
    --protocol tcp \
    --port 5432 \
    --source-group ${SGID}

SUBNETRESULT1=$(aws ec2 create-subnet \
    --cidr-block 10.0.1.0/24 \
    --vpc-id "${VPCID}" \
    --availability-zone us-east-1e)

SUBNETRESULT2=$(aws ec2 create-subnet \
    --cidr-block 10.0.2.0/24 \
    --vpc-id "${VPCID}" \
    --availability-zone us-east-1f)

SUBNETID1=$(echo ${SUBNETRESULT1} | jq -r '.Subnet.SubnetId')
SUBNETID2=$(echo ${SUBNETRESULT2} | jq -r '.Subnet.SubnetId')

ASSOCIATERTRESULT1=$(aws ec2 associate-route-table \
    --route-table-id ${ROUTETABLEID} \
    --subnet-id ${SUBNETID1})

ASSOCIATERTRESULT2=$(aws ec2 associate-route-table \
    --route-table-id ${ROUTETABLEID} \
    --subnet-id ${SUBNETID2})

PUBLICIPSUBNETRESULT1=$(aws ec2 modify-subnet-attribute \
    --subnet-id ${SUBNETID1} \
    --map-public-ip-on-launch)

PUBLICIPSUBNETRESULT2=$(aws ec2 modify-subnet-attribute \
    --subnet-id ${SUBNETID2} \
    --map-public-ip-on-launch)

RDSSUBNETRESULT=$(aws rds create-db-subnet-group \
    --db-subnet-group-name ultitracker-api-db-subnet \
    --db-subnet-group-description "DB Security group for ultitracker-api db" \
    --subnet-ids "${SUBNETID1}" "${SUBNETID2}")

RDSCREATERESULT=$(aws rds create-db-instance \
    --db-name ${POSTGRES_DATABASE} \
    --db-instance-identifier ultitracker-api-db \
    --db-instance-class ${POSTGRES_INSTANCE_CLASS} \
    --allocated-storage ${POSTGRES_ALLOCATED_STORAGE} \
    --engine postgres \
    --engine-version 10.6 \
    --master-username ${POSTGRES_USERNAME} \
    --master-user-password ${POSTGRES_PASSWORD} \
    --db-subnet-group-name ultitracker-api-db-subnet \
    --vpc-security-group-ids "${SGID}")

aws s3api create-bucket \
    --bucket ${S3_BUCKET_NAME} \
    --acl private \
    --region us-east-1

# upload ssl cert to iam
SSLCERTRESULT=$(aws iam upload-server-certificate \
    --server-certificate-name api.ultitracker.com \
    --certificate-body file://${LETSENCRYPTFOLDER}/live/api.ultitracker.com/fullchain.pem \
    --private-key file://${LETSENCRYPTFOLDER}/live/api.ultitracker.com/privkey.pem)

SSLCERTARN=$(echo ${SSLCERTRESULT} | jq -r '.ServerCertificateMetadata.Arn')