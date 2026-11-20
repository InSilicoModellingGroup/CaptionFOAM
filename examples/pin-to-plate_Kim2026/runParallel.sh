#!/bin/bash
#SBATCH --job-name=comsol2
#SBATCH --output=mpijob.%x_%j.out
#SBATCH --error=mpijob.%x_%j.err
#SBATCH --ntasks=320
#SBATCH --nodes=8
#SBATCH --exclusive
#SBATCH --mem-per-cpu=2G
#SBATCH --partition=COMPUTE
#SBATCH --time=4-00:00:00

./Allmesh

./runParallel