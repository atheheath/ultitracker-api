# Ultitracker API This package hosts the functionality for data control within ultitracker. 

# Deployment Process
We use Elastic Beanstalk's [Docker configuration environment](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/single-container-docker-configuration.html) to deploy these processes. We use a load balancer on top of the containers to route the traffic.

## Deployment Steps
* Make `prod.dockerfile` the active `Dockerfile`
    * `cp ./prod.dockerfile ./Dockerfile`
* Create the release zip
    * `./create-eb-release-zip.sh`
* Upload and deploy that zip to the elastic beanstalk environment

# Develop Environment
* Build the local image
    * `./docker-build-dev.sh`
* Run the local image
    * './docker-run-dev.sh`
* Typical test account is
    * username: `test`, password: `test`

# Connect to postgres instance
* ssh into an existing instance
* Connect to docker instance
    * `sudo docker exec -it <docker_name> bash`
* Run psql command to connect
    * `psql --host=${POSTGRES_HOSTNAME} --username=${POSTGRES_USERNAME}`
* List databases and tables
    * `select * from information_schema.tables where table_schema = 'ultitracker'` 
