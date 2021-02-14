# load general packages and functions
import csv
import os
import subprocess
import time

# example submission script



# define what you want to do for the specified job(s)
dataset = "Toxic"
job_type = "preprocess"       # "preprocess", "train", "generate", or "test"
jobdir_start_idx = 0     # where to start indexing job dirs
n_jobs = 1               # number of jobs to run per model
restart = False
force_overwrite = False  # overwrite job directories which already exist
jobname = "toxicology"      # used to create a sub directory

# if running using SLURM, specify the parameters below
use_slurm = False        # use SLURM or not
run_time = "1-00:00:00"  # hh:mm:ss
mem_GB = 20

# set paths here
python_path = f"/usr/local/bin/python3.8"
graphinvent_path = f"./graphinvent/"
data_path = f"./data/"

# define dataset-specific parameters
params = {
    "atom_types": ['B', 'C', 'N', 'O', 'F', 'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'K', 'Ca', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ge', 'As', 'Se', 'Br', 'Zr', 'Ag', 'Cd', 'Sn', 'I', 'Ba', 'W', 'Au', 'Hg', 'Pb', 'Bi'],
    "formal_charge": [-2,-1, 0, +1,+2,+3,+4],
    "max_n_nodes": 155,
    "job_type": job_type,
    "dataset_dir": f"{data_path}{dataset}/",
    "restart": restart,
    "model": "GGNN",
    "sample_every": 10,
    "init_lr": 1e-4,
    "min_rel_lr": 5e-2,  # use 1e-3 for larger datasets
    "lrdf": 0.9999,
    "lrdi": 100,
    "epochs": 400,
    "batch_size": 1000,
    "block_size": 100000,
    # additional paramaters can be defined here, if different from the "defaults"
    # (!!!) for "generate" jobs, don't forget to specify "generation_epoch" and "n_samples"
}


# set partition to run job on
if job_type == "preprocess":  # preprocessing jobs CPU only
    partition = "core"
    cpus_per_task = 1
else:
    partition = "gpu"
    cpus_per_task = 4


def submit():
    """ Creates and submits submission script. Uses global variables defined at
    top of this file.
    """
    check_paths()

    # create an output directory
    data_path_minus_data = data_path[:-5]
    dataset_output_path = f"{data_path_minus_data}output_{dataset}"
    tensorboard_path = os.path.join(dataset_output_path, "tensorboard")
    if jobname != "":
        dataset_output_path = os.path.join(dataset_output_path, jobname)
        tensorboard_path = os.path.join(tensorboard_path, jobname)

    os.makedirs(dataset_output_path, exist_ok=True)
    os.makedirs(tensorboard_path, exist_ok=True)
    print(f"* Creating dataset directory {dataset_output_path}/", flush=True)

    # submit `n_jobs` separate jobs
    jobdir_end_idx = jobdir_start_idx + n_jobs
    for job_idx in range(jobdir_start_idx, jobdir_end_idx):

        # specify and create the job subdirectory if it does not exist
        params["job_dir"] = f"{dataset_output_path}/job_{job_idx}/"
        params["tensorboard_dir"] = f"{tensorboard_path}/job_{job_idx}/"

        # create the directory if it does not exist already, otherwise raises an error,
        # which is good because *might* not want to override data our existing directories!
        os.makedirs(params["tensorboard_dir"], exist_ok=True)
        try:
            os.makedirs(params["job_dir"],
                        exist_ok=bool(job_type in ["generate", "test"] or force_overwrite))
            print(
                f"* Creating model subdirectory {dataset_output_path}/job_{job_idx}/",
                flush=True,
            )
        except FileExistsError:
            print(
                f"-- Model subdirectory {dataset_output_path}/job_{job_idx}/ already exists.",
                flush=True,
            )
            if not restart:
                continue

        # write the `input.csv` file
        write_input_csv(params_dict=params, filename="input.csv")

        # write `submit.sh` and submit
        if use_slurm:
            print("* Writing submission script.", flush=True)
            write_submission_script(job_dir=params["job_dir"],
                                    job_idx=job_idx,
                                    job_type=params["job_type"],
                                    max_n_nodes=params["max_n_nodes"],
                                    runtime=run_time,
                                    mem=mem_GB,
                                    ptn=partition,
                                    cpu_per_task=cpus_per_task,
                                    python_bin_path=python_path)

            print("-- Submitting job to SLURM.", flush=True)
            subprocess.run(["sbatch", params["job_dir"] + "submit.sh"])
        else:
            print("* Running job as a normal process.", flush=True)
            subprocess.run(["ls", f"{python_path}"])
            subprocess.run([f"{python_path}",
                            f"{graphinvent_path}main.py",
                            "--job-dir",
                            params["job_dir"]])

        # sleep a few secs before submitting next job
        print(f"-- Sleeping 2 seconds.")
        time.sleep(2)


def write_input_csv(params_dict, filename="params.csv"):
    """ Writes job parameters/hyperparameters in `params_dict` (`dict`) to CSV
    using the specified `filename` (`str`).
    """
    # write the parameters to CSV
    dict_path = params_dict["job_dir"] + filename

    with open(dict_path, "w") as csv_file:

        writer = csv.writer(csv_file, delimiter=";")
        for key, value in params_dict.items():
            writer.writerow([key, value])


def write_submission_script(job_dir, job_idx, job_type, max_n_nodes, runtime,
                            mem, ptn, cpu_per_task, python_bin_path,):
    """ Writes a submission script (`submit.sh`).

    Args:
      job_dir (str) : Job running directory.
      job_idx (int) : Job idx.
      job_type (str) : Type of job to run.
      max_n_nodes (int) : Maximum number of nodes in dataset.
      runtime (str) : Job run-time limit in hh:mm:ss format.
      mem (int) : Gigabytes to reserve.
      ptn (str) : Partition to use, either "core" (CPU) or "gpu" (GPU).
      python_bin_path (str) : Path to Python binary to use.
    """
    submit_filename = job_dir + "submit.sh"
    with open(submit_filename, "w") as submit_file:
        submit_file.write("#!/bin/bash\n")
        submit_file.write(f"#SBATCH --job-name={job_type}{max_n_nodes}_{job_idx}\n")
        submit_file.write(f"#SBATCH --output={job_type}{max_n_nodes}_{job_idx}o\n")
        submit_file.write(f"#SBATCH --time={runtime}\n")
        submit_file.write(f"#SBATCH --mem={mem}g\n")
        submit_file.write(f"#SBATCH --partition={ptn}\n")
        submit_file.write("#SBATCH --nodes=1\n")
        submit_file.write(f"#SBATCH --cpus-per-task={cpu_per_task}\n")
        if ptn == "gpu":
            submit_file.write(f"#SBATCH --gres=gpu:1\n")
            submit_file.write("module load CUDA\n")  # TODO is this needed?
        submit_file.write("hostname\n")
        submit_file.write("export QT_QPA_PLATFORM='offscreen'\n")
        submit_file.write(f"{python_bin_path} {graphinvent_path}main.py --job-dir {job_dir}")
        submit_file.write(f" > {job_dir}output.o${{SLURM_JOB_ID}}\n")


def check_paths():
    """ Checks that paths to Python binary, data, and GraphINVENT are properly
    defined before running a job, and tells the user to define them if not.
    """
    for path in [python_path, graphinvent_path, data_path]:
        if "path/to/" in path:
            print("!!!")
            print("* Update the following paths in `submit.py` before running:")
            print("-- `python_path`\n-- `graphinvent_path`\n-- `data_path`")
            exit(0)

def visualize(smi_file):
  import random
  import math
  from rdkit.Chem.Draw import MolsToGridImage
  from rdkit.Chem.rdmolfiles import SmilesMolSupplier

  # load molecules from file
  mols = SmilesMolSupplier(smi_file, sanitize=True, nameColumn=-1)

  n_samples = 100
  mols_list = [mol for mol in mols]
  mols_sampled = random.sample(mols_list, n_samples)  # sample 100 random molecules to visualize

  mols_per_row = int(math.sqrt(n_samples))            # make a square grid

  png_filename=smi_file[:-3] + "png"  # name of PNG file to create
  print(png_filename)
  labels=list(range(n_samples))       # label structures with a number

  # draw the molecules (creates a PIL image)
  img = MolsToGridImage(mols=mols_sampled,
                        molsPerRow=mols_per_row,
                        legends=[str(i) for i in labels])

  img.save(png_filename)
if __name__ == "__main__":
    visualize("data/Toxic/train.smi")
    visualize("data/Toxic/valid.smi")
    visualize("data/Toxic/test.smi")
    submit()

    
