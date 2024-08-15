cd sandbox

if [ "$1" == "--pull" ]; then
    sudo docker pull kromiose/nekro-agent-sandbox
fi

if [ "$1" == "--build" ]; then
    sudo rm -rf .venv
    sudo rm -rf poetry.lock
    sudo docker build -t nekro-agent-sandbox:latest .
fi

if [ "$1" == "--push" ]; then
    sudo docker tag nekro-agent-sandbox:latest kromiose/nekro-agent-sandbox:latest
    sudo docker push kromiose/nekro-agent-sandbox:latest
fi
