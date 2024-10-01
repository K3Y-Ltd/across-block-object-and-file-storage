# Block Object and File Storage

This repository holds the installation of Block Object and File Storage service that has been developed and deployed during ACROSS project. It serves as a File Storage solution that has a 
During the ACROSS project, the Block Object and File Storage has been configured using [Minio](https://min.io/). This documentation file holds the necessary steps to be followed in order to deploy an instance on a cloud VM.

### File information

- **Creator**: Evangelos Syrmos
- **PowerPoint Presentation**: [k3y.sharepoint](https://k3ybggr.sharepoint.com/:p:/s/K3Y/EbIaXg0DTKNCmaOA_CNQ1m8BTKhnkVoaQ3H5XVzMJJPBDg?e=fEnJ8q)
- **Date**: November 2023
- **Related Project**: ACROSS

## Prerequisites

In order to run the following tutorial make sure to have installed the following tools on the host machine:

    1) Docker engine
    2) docker compose
    3) Python
    4) virtual env

## Minio

Minio is an open source software tool that facilites the storage of files in be leveraging the underlying file system.
The software architecture that describes Minio is a bucket oriented solution, where each bucket is designeted to store large files with the ability to retrieve them via `minio clients` that interface with the exposed API. A REST API based on FastAPI is provided to interface with the underlying Minio instance.

Minio exposes two ports: - 9000: Used for interfacing with the underlying REST API via the selected minion clients depending the used programming language. - 9090: Used for providing the management dashboard. **_NOTE_**: This should **_NOT_** be exposed publicly for security measures.

### Docker deployment

The following `docker-compose.yml` file is a preliminary implementation that creates a shared volume between the host machine and the docker container itself. This ensures the persistency of the data in unpresidented of containers' failure under the `/minio-data` folder that will be create when the container starts.

**_NOTE_**
Before you start the container specify the credientials for loggin in the minio dashboard by changing the values in the `.env.local` file. The values that need to be changed are `MINIO_ROOT_USER` & `MINIO_ROOT_PASSWORD`.

```docker
version: "3.8"

services:
    minio:
        image: quay.io/minio/minio:latest
        container_name: minio
        restart: always
        ports:
          - 9000:9000
          - 9090:9090
        environment:
            MINIO_ROOT_USER: ${MINIO_ADMIN_USERNAME}
            MINIO_ROOT_PASSWORD: ${MINIO_ADMIN_PASSWORD}
        volumes:
          - minio_data:/minio_data
        command: server /data --console-address ":9090"

volumes:
    minio_data:
```

In order to start the container run `docker-compose up -d`, this will pull the latest minio image from the docker hub and start the container.

### Dashboard

Specify the credential in the `.env.local` `MINIO_ADMIN_USERNAME= "admin"`, `MINIO_ADMIN_PASSWORD= "admin"` file.
Then spinn up the container and visit the ip address of the host machine on port `9090`. 
Signin with the credentials you specified on the `docker-compose.yml` file, namely `MINIO_ROOT_USER` & `MINIO_ROOT_PASSWORD`.

Once you signin you need to create a bucket with the same name that you will provide in the `.env` file.

Additionaly, you must create a pair of `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` to pass to the client library in order to interface with the minio REST API.

## Environment variables

In the same directory as the python REST APIs create a `.env` file that stores the secret variables that will be read when executing each python script.

```bash
MINIO_ADDRESS = "localhost:9000"
MINIO_ACCESS_KEY = "your_minio_access_key"
MINIO_SECRET_KEY = "your_minio_secret_key"
```

## FastAPI

Fast API was used as an intermediate interface solution that acts as main REST API that exteranl client requests can be done, thus reducing the public exposure of Minio.

### Libraries

The core libraries that you will need in order to run the following python REST API on a cloud VM are:

1. `pip install fastapi`
2. `pip install python-dotenv`
3. `pip install minio`
4. `pip install "uvicorn[standard]"`

### Run

To execute the REST API run the following command on the terminal:
`uvicorn rest-api:app --host 0.0.0.0 --port 5000`

In case you want to run it in the background run the following command:
`nohup uvicorn rest-api:app --host 0.0.0.0 --port 5000 > uvicorn_output.log 2>&1 &`

### OpenAPI - Swagger - API Reference

An OpenAPI file is also provided via the `swagger.json` file that can also be viewed via `{IP_ADDRESS}:5000/docs` or `{IP_ADDRESS}:5000/redocs`.
