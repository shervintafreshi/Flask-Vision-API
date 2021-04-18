#!/bin/sh
gunicorn app:app -w 3 --threads 2 -b 0.0.0.0:8080 --log-level=debug --timeout 120