#!/bin/sh

set -e

docker build -f environment/Dockerfile -t ghcr.io/geffenlab/geffenlab-bombcell:local .

docker run --rm \
  --user $(id -u):$(id -g) \
  --volume /home/ninjaben/codin/geffen-lab-data/processed_data/BH/AS20-minimal3/03112025/:/home/ninjaben/codin/geffen-lab-data/processed_data/BH/AS20-minimal3/03112025/ \
  --volume /home/ninjaben/codin/geffen-lab-data/processed_data/BH/AS20-minimal3/03112025/kilosort4:/home/ninjaben/codin/geffen-lab-data/processed_data/BH/AS20-minimal3/03112025/kilosort4 \
  ghcr.io/geffenlab/geffenlab-bombcell:local \
  /home/ninjaben/codin/geffen-lab-data/processed_data/BH/AS20-minimal3/03112025/kilosort4
