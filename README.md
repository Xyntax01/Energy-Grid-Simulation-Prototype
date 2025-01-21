# Energy grid simulation prototype
This prototype simulates a grid network to develop an algorithm based on congestion.

## Prerequisites

To run the simulation, ensure you have [Docker](https://www.docker.com/get-started/) installed.

## Running the Simulation

Execute the following command to build the Docker image, start the container, and log the output:

```bash
docker compose up -d --build && docker logs simulation -n 0 -f
```

Docker will build the python image with the latest code, start the container and log the output to your console.

## Spade

Spade is a Multi-Agent Based (MAS) simulation framework that is used by the simulation. The official documentation can be found at [spade-mas.readthedocs.io](https://spade-mas.readthedocs.io/en/latest/index.html).

## Nox usage

[`nox`](https://nox.thea.codes/en/stable/index.html) is a command-line tool that automates testing in multiple Python environments, similar to [tox](https://tox.readthedocs.org/).

To run the tests, run the following command:

```bash
nox
```

To see the code coverage in more detail, open the `htmlcov\index.html` file.

## Configuring a network

A network with assets can be configured using a yaml configuration file. This file configures a root network and defines all the other assets and (sub)networks as it's children. Documentation and an example configuration file can be found [here](./docs/configuration.md).

## Instantiating nodes

## Adding a new agent

- Create a new class that implements `spade.agent.Agent`.
- Create a new behaviour class that implements e.g., `CyclicBehaviour` and create an instance called `self.behaviour` in
  the agent class.
- In the agent class, create an async function called `setup`.
- In this function, call `self.add_behaviour(self.behaviour)` with the behaviour class to implement this behaviour.
