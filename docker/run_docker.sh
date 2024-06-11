docker rm openpose
docker run --gpus all --runtime=runc --interactive -it --shm-size=10gb --env="DISPLAY" --volume="/home/robot/projects/openpose-docker:/home/openpose_user/src/openpose" --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" --workdir="/home/openpose_user/src/openpose/finger_tracking_ws" -p 6017:6017 --privileged --name=openpose openpose:latest
# docker exec -it openpose2 bash
