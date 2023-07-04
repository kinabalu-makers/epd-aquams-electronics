#!/bin/bash

directory=$(pwd)

# if [ -d "$directory/venv" ]; then
#     echo "Directory already exists"
# else
#     echo "Creating virtual environment"
#     (cd "$directory" && python3 -m venv venv)
#     sleep 20
# fi

echo "Activating virtual environment"
source "$directory"/venv/bin/activate

# echo "Installing requirements"
# pip install -r "$directory"/requirements.txt

echo "Running main.py"
python "$directory"/main.py

echo "Copy file to file server direcories"
cp -r "$directory"/ESP32/* /home/pi/file_server/ESP32