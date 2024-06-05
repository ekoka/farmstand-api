#!/bin/bash

#gunicorn --workers 2 --pid /tmp/gunicorn.pid --bind 0.0.0.0:5000 --log-level debug --error-logfile ./logs/gunicorn.error.log --access-logfile ./logs/gunicorn.access.log wsgiapi:app
#gunicorn --workers 5 --bind 0.0.0.0:5000 wsgiapi:app
gunicorn --workers 2 --bind 0.0.0.0:5000 --log-level debug --error-logfile ./logs/gunicorn.error.log --access-logfile ./logs/gunicorn.access.log wsgiapi:app
