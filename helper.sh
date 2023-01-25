#!/bin/bash
uvicorn run:app --reload --workers 4
lsof -nti:8000 | xargs kill -9