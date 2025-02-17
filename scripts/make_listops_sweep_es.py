# Create a script to run a random hyperparameter search.

import copy
import getpass
import os
import random
import numpy as np
import gflags
import sys

NYU_NON_PBS = False
NAME = "listops20s_07_28"
SWEEP_RUNS = 20

LIN = "LIN"
EXP = "EXP"
BOOL = "BOOL"
CHOICE = "CHOICE"
SS_BASE = "SS_BASE"

FLAGS = gflags.FLAGS

gflags.DEFINE_string("training_data_path", "spinn/data/listops/train_d20s.tsv", "")
gflags.DEFINE_string("eval_data_path", "spinn/data/listops/test_d20s.tsv", "")
gflags.DEFINE_string("log_path", "/scratch/nn1119/spinn/sweep", "")

FLAGS(sys.argv)

# Instructions: Configure the variables in this block, then run
# the following on a machine with qsub access:
# python make_sweep.py > my_sweep.sh
# bash my_sweep.sh

# - #

# Non-tunable flags that must be passed in.

FIXED_PARAMETERS = {
    "data_type":     "listops",
    "model_type":      "SPINN",
    "training_data_path":    FLAGS.training_data_path,
    "eval_data_path":    FLAGS.eval_data_path,
    "log_path": FLAGS.log_path,
    "ckpt_path":  FLAGS.log_path,
    "word_embedding_dim":   "64",
    "model_dim":   "64",
    "eval_seq_length":  "3000",
    "eval_interval_steps": "100",
    "statistics_interval_steps": "100",
    "batch_size":  "64",
    "encode": "pass",
    "mlp_dim": "16",
    "num_mlp_layers": "2",
    "semantic_classifier_keep_rate": "1.0",
    "embedding_keep_rate": "1.0",
    "sample_interval_steps": "1000",
    "nocomposition_ln": "",
    "learning_rate": "0.00641719241862",
    "seq_length": "100",
}

# Tunable parameters.
SWEEP_PARAMETERS = {
    "l2_lambda":          ("l2", EXP, 8e-7, 1e-3),
    "learning_rate" : ("lr", EXP, 1e-2, 8e-2),
    "learning_rate_decay_when_no_progress": ("dc", LIN, 0.3, 1.0),
    "es_num_episodes" : ("eps", LIN, 4, 6),
    "es_num_roots" : ("roots", LIN, 2, 5),
    "es_episode_length" : ("lng", LIN, 200, 800),
}

sweep_name = "sweep_" + NAME + "_" + \
    FIXED_PARAMETERS["data_type"] + "_" + FIXED_PARAMETERS["model_type"]

# - #
print("# NAME: " + sweep_name)
print("# NUM RUNS: " + str(SWEEP_RUNS))
print("# SWEEP PARAMETERS: " + str(SWEEP_PARAMETERS))
print("# FIXED_PARAMETERS: " + str(FIXED_PARAMETERS))
print()

for run_id in range(SWEEP_RUNS):
    params = {}
    name = sweep_name + "_" + str(run_id)

    params.update(FIXED_PARAMETERS)
    # Any param appearing in both sets will be overwritten by the sweep value.

    for param in SWEEP_PARAMETERS:
        config = SWEEP_PARAMETERS[param]
        t = config[1]
        mn = config[2]
        mx = config[3]

        r = random.uniform(0, 1)
        if t == EXP:
            lmn = np.log(mn)
            lmx = np.log(mx)
            sample = np.exp(lmn + (lmx - lmn) * r)
        elif t == BOOL:
            sample = r > 0.5
        elif t==SS_BASE:
            lmn = np.log(mn)
            lmx = np.log(mx)
            sample = 1 - np.exp(lmn + (lmx - lmn) * r)
        elif t==CHOICE:
            sample = random.choice(mn)
        else: # LIN
            sample = mn + (mx - mn) * r

        if isinstance(mn, int):
            sample = int(round(sample, 0))
            val_disp = str(sample)
            params[param] = sample
        elif isinstance(mn, float):
            val_disp = "%.2g" % sample
            params[param] = sample
        elif t==BOOL:
            val_disp = str(int(sample))
            if not sample:
                params['no' + param] = ''
            else:
                params[param] = ''
        else:
            val_disp = sample
            params[param] = sample
        name += "-" + config[0] + val_disp

    flags = ""
    for param in params:
        value = params[param]
        flags += " --" + param + " " + str(value)
        if param == "es_num_episodes":
            a = value
        if param == "es_num_roots":
            b = value

    flags += " --experiment_name " + name
    if NYU_NON_PBS:
        print("cd spinn/python; python3 -m spinn.models.supervised_classifier " + flags)
    else:
        print("SPINN_FLAGS=\"" + flags + "\" bash ../scripts/sbatch_submit_es_cpu_only.sh")
        print(a * b)
    print()
