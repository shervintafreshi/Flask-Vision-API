#!/bin/sh
gunicorn app:app -w 3 --threads 3 -b 0.0.0.0:8080 --timeout 120