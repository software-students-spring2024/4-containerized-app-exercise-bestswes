![Lint-free](https://github.com/nyu-software-engineering/containerized-app-exercise/actions/workflows/lint.yml/badge.svg)

# Containerized App Exercise

Welcome to Chequemate 2.0, the premier place to scan receipts and split them with your friends.

This project is an extension of our [first specification project](https://github.com/software-students-spring2024/1-specification-exercise-bestswegroup) and [second project](https://github.com/software-students-spring2024/2-web-app-exercise-bswe) which defined and implemented a bill splitting web app. The goal of this exericse is to build a containerized app that uses machine learning. See [instructions](./instructions.md) for details.

In this project, we redesigned the frontend, containerized the web app and database, and added an OCR machine learning container for receipt scanning + parsing.

# Team Members

[Edison Chen](https://github.com/ebc5802), [Natalie Wu](https://github.com/nawubyte), [Chelsea Li](https://github.com/qiaoxixi1), and [Jacklyn Hu](https://github.com/Jacklyn22)

# How To Run ChequeMate

## From the root dir, run

`docker compose up --build`

## To build + run docker containers locally for ml_client + web_app + db:
In one terminal,

`docker network create ChequeMate`

`cd web_app/`

`docker build -t web_app_image .`

`docker run -it --rm --name web_app_container -p 5000:5000 --network ChequeMate web_app_image`

In another terminal,

`cd machine_learning_client`

`docker build -t ml_client_image .`

`docker run -it --rm --name ml_client_container -p 5001:5001 --network ChequeMate ml_client_image`

In another another terminal,

`docker run --name mongodb -d -p 27017:27017 --network ChequeMate mongo`

The three containers are now connected through a docker network.

# Credits

ML client based off tutorial by [NeuralNine](https://www.youtube.com/watch?v=dSCJ7DImGdA) using the asprise OCR API.

README run instructions referenced from [Team Speedy](https://github.com/software-students-spring2024/4-containerized-app-exercise-speedy)