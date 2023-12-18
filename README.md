# Pineapple Experiment Automation
This repo consists of python code that will autonomously run the replication protocol experiments cited in our paper ("Pineapple: Unifying Multi-Paxos and Atomic Shared Registers") and plot them. See `config_instruction.md` for information on available configs.

## Table of Contents
- **Dependencies**
  - Code
  - Repos
  - Cloudlab
- **How to Run**
    - Setup
    - Running experiment
    - Plotting
## Dependencies and Setup
### Code
- Go 1.15 (for replication protocol code)
- Python 3.10 (for running experiments automatically, calculating stats, plotting data)
    - NumPy
        - Install with ```pip install numpy```
    - PrettyTable
        - Install with ```python -m pip install -U prettytable```
    - Matplotlib
        - Install with ```pip install matplotlib```
- GNUPlot
    - See [here](https://riptutorial.com/gnuplot/example/11275/installation-or-setup) to install
### Repositories
- The Pineapple repository: ``https://github.com/tigranb2/pineapple``
- The Gus and Epaxos repository: ``https://github.com/tigranb2/gus-epaxos``
    - Note: this implementation only sports non conflicting operations.
- The Gryff repository: ``https://github.com/tigranb2/gryff-testing``
    - Note: Both ``gryff-testing`` and ``gus-epaxos`` repositories are derived from the EPaxos repository, but have different communication between clients and servers, so it is easier to have two separate repos.
### Cloudlab Profile
It is easiest to run the experiments by used the pre-configured profile on Cloudlab, which already has all necessary repositories and dependencies installed. The profile can be instantiated [here](https://www.cloudlab.us/instantiate.php?profile=b5d01b37-541e-11ee-b28b-e4434b2381fc).

## How to Run
### Setup
1. Connect to the control machine via ssh.
``` 
ssh -i <path-to-ssh-key> -p 22 -A <root/userid>@<public dns/ip>
```
   - The final address is the address of the **CONTROL** node. 
   - Make sure to include `-A` as an ssh argument
      - This enables port forwarding and allows the control machine to run remote commands over ssh on the other replicas.
2. Open ``gus-automation`` in the control machine. This repo and others can be found in `/root/go/src`. All repos are stored in root because cloudlab disk images do not save data stored in user home directories.
```
sudo su
cd ~/go/src/gus-automation
```

3. Make sure ``gus-automation`` is up to date.
```
git pull
```
   - If this doesn't work, run ```git reset --hard LATEST_COMMIT``` where LASTEST_COMMIT is the latest commit to the repo on github to update code
4. Recompile protocol code to ensure it's updated.
```
python3 compile_protocols.py
```

### RMWFig6.json
For this experiment, use the open-loop client version of the protocols. Visit each protocol's directory and checkout the ``open-loop-client`` branch. Remember to run the ``compile.sh`` in each protocol's directory after each branch change to recompile the protocol binaries. 

All other experiments are performed on the default branch (``main``).
### Running experiment
1. Go to gus-automation:
```
cd ~/go/src/gus-automation
```
2. If CloudLab experiment has a name other than “test”, set the experiment name with:
```
python3.8 set_experiment_name.py [CLOUDLAB_EXPERIMENT_NAME]
```
3. Run an experiment with the following command, filling in the name appropriately
```
python3.8 run_experiments.py [EXPERIMENT_CONFIG_NAME]
```
- The result will be output to a time-stamped folder in ~/go/src/gus-automation/results.


### Plotting
To plot, you can either move the result folder onto your local machine or continue on Cloudlab.
1. Go to plotFigs folder
```
cd ~/go/src/gus-automation/plotFigs
```
2. Run the following, which will plot the data in the latest timestamp folder:
```
python3.8 plot_figs.py
```
- The plots will be in the plots folder


----