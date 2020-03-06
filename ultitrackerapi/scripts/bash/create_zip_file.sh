HEADDIR=$1

if [[ "${HEADDIR}" == "" ]]
then
    echo "Need to pass in directory to zip"
    exit 1
fi 

pushd ${HEADDIR}

pip install --target ./package ffmpeg-python

pushd ./package
zip -r9 -q ../aws_function.zip .
popd

pushd static/ffmpeg-4.2.2-amd64-static
cp ffmpeg ffmpeg_bin
zip -g ../../aws_function.zip ffmpeg_bin
rm ffmpeg_bin
popd

pushd scripts/python
zip -g ../../aws_function.zip aws_lambda_extract_frames.py
popd

popd
