#!/bin/bash

if [ ! $(command -v pip3) ]; then
    sudo apt install python3-pip
fi

pip3 install dash
pip3 install requests
pip3 install pandas