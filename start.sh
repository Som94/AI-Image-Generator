#!/bin/bash
gunicorn -b 0.0.0.0:8080 main:app