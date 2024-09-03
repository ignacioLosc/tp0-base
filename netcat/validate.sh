#!/bin/sh
testvalue='validate server'
result=$(echo $testvalue| nc -q 1 server 12345)
if [[ "$testvalue" == "$result" ]];
then
    echo 'action: test_echo_server | result: success';
else
echo 'action: test_echo_server | result: fail';
fi
