# docker exec netcat ./validate.sh
# docker run --rm -dit --name netcat $(docker build -q ./netcat) && docker exec netcat ./validate.sh
docker run --rm -dit --name netcat --net tp0_testing_net $(docker build -q ./netcat) && docker exec netcat ./validate.sh