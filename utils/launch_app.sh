#!/bin/bash

# This script is used to launch an application on the device.
lsof -nti:8000 | xargs kill -9

uvicorn run:app --reload --workers 4

