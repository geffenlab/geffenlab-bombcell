# geffenlab-bombcell

This repository defines a processing step that is part of the [geffenlab-ephys-pipeline](https://github.com/geffenlab/geffenlab-ephys-pipeline).

This "bombcell" step reads a folder of [Phy](https://github.com/cortex-lab/phy) data, as produced by [Kilosort4](https://github.com/MouseLand/Kilosort), and runs[Bombcell](https://github.com/Julie-Fabre/bombcell/tree/main/py_bombcell) to create diagnostic plots and quality control metrics.  It contains a Python wrapper to facilitate finding Kilosort results across sessions, and invoking Bombcell for each session.

# Lifecycle of a processing step

This repository defines the processing step's [environment](./environment/), including dependencies and custom Python [code](./code/).  These can be edited, committed, and pushed to this repository on GitHub.

This repository is the source of truth for the step's environment and code, but we don't run the code directly from here.  Instead we package the environment and code from this repository into a [Docker image](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-an-image/).  This makes the step portable and reproducible.

The [geffenlab-ephys-pipeline](https://github.com/geffenlab/geffenlab-ephys-pipeline) defines pipelines in terms of our Docker images.  [Here's an example](https://github.com/geffenlab/geffenlab-ephys-pipeline/blob/master/proceed/as-nidq.yaml#L41) of where a pipeline refers to one of our Docker images.

## Creating new nersions of the Docker image

This repository is configured to automatically build and publish a new Docker image, each time a [repository tag](https://git-scm.com/book/en/v2/Git-Basics-Tagging) is pushed to GitHub.

The published images are located in the GitHub Container Registry as [geffenlab-bombcell](https://github.com/benjamin-heasly/geffenlab-bombcell/pkgs/container/geffenlab-bombcell).  You can find the latest and previous versions of the step's Docker image there.

## Example update workflow

Here's a workflow for building and realeasing a new Docker image version.

First, make changes to the code in this repo, and `push` the changes to GitHub.

```
# Edit code
git commit -a -m "Now with lasers!"
git push
```

Next, create a new repository [tag](https://git-scm.com/book/en/v2/Git-Basics-Tagging), which marks your commit as important and gives it a unique name and description.  For the unique tag name we use version numbers like `v0.0.5`.

```
# Review existing tags and choose the next version number to use.
git pull --tags
git tag --list

# Create the tag for the next version
git tag -a v0.0.5 -m "Now with lasers!"
git push --tags
```

When you `git push --tags`, GitHub will detect your new version and kick off a fresh Docker image build.  The new image will contain the environment and code from this repository, as of your tagged commit.

You can see the code for this automated workflow in this repository at [build-tag.yml](./.github/workflows/build-tag.yml).

You can follow the progress of the Docker image build at the step [Actions](https://github.com/benjamin-heasly/geffenlab-bombcell/actions) page.  When the build completes you should see a new [published version](https://github.com/benjamin-heasly/geffenlab-bombcell/pkgs/container/geffenlab-bombcell) with the version tag you provided, like `v0.0.5`.

## Update your pipeline

When your step's new Docker image is ready you can update your pipeline to refer to the new version.  This means updating the version number in your pipeline YAML, for example [here](https://github.com/geffenlab/geffenlab-ephys-pipeline/blob/master/proceed/as-nidq.yaml#L41).  The next time you run your pipeline it will download the newer Docker image version that you specified, and use that version of the environment and code.

### older verions are still OK

Existing pipelines that refer to older Docker image versions should continue to work as-is, even after you create a new version.  Older Docker images will remain, saved on GitHub, available for use.

This means new image versions are always optional.  You can update your pipelines to use new versions when you're ready.  Different people and different pipelines can use different versions of the same step without interference.
