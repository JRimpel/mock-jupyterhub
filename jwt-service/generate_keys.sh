#!/usr/bin/env bash

openssl genrsa -out jwt-key 2048
openssl pkey -in jwt-key -pubout -out jwt-key.pub
