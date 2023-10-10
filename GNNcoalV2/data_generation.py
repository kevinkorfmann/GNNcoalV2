# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/data_generation.ipynb.

# %% auto 0
__all__ = ['sample_constant_population_size', 'sample_population_size', 'get_population_time', 'simulate_scenario',
           'sample_parameters', 'sample_smooth_population_parameters', 'simulate_tree_sequence', 'generate_sample',
           'alternative_coalescent_mask']

# %% ../nbs/data_generation.ipynb 1
import numpy as np
import pandas as pd
from typing import Union
from scipy.interpolate import interp1d
import tskit
from tqdm import tqdm
import msprime

# %% ../nbs/data_generation.ipynb 2
def sample_constant_population_size(n_min:int=10, n_max:int=100_000, num_time_windows=21) -> list[float]:
    return np.random.uniform(n_min, n_max, 1).tolist() * num_time_windows

# %% ../nbs/data_generation.ipynb 3
def sample_population_size(n_min:int=10, n_max:int=100_000, num_time_windows=21) -> list[float]:
    
    """Creates random demography. Function taken from: 
    https://gitlab.inria.fr/ml_genetics/public/dlpopsize_paper
    
    :param int n_min: Lower-bound of demography.
    :param int n_max: Upper-bound of demography.
    :param int num_time_windows: Number of population sizes in demography.
    :return list: 
    """
    
    n_min_log10 = np.log10(n_min)
    n_max_log10 = np.log10(n_max)
    population_size = [10 ** np.random.uniform(low=n_min_log10, high=n_max_log10)] 
    for j in range(num_time_windows - 1):
        population_size.append(10 ** n_min_log10 - 1)
        while population_size[-1] > 10 ** n_max_log10 or population_size[-1]  < 10 ** n_min_log10:
            population_size[-1] = population_size[-2] * 10 ** np.random.uniform(-1, 1)
            
    return population_size

# %% ../nbs/data_generation.ipynb 4
def get_population_time(time_rate:float=0.06, tmax:int = 130_000,
                        num_time_windows:int = 21
                       ) -> np.array :
    """Creates population time points; used as time points to change
    population size changes for simulation
    
    :return numpy.ndarray: time points of length num_time_windows
    """
    
    population_time = np.repeat([(np.exp(np.log(1 + time_rate * tmax) * i /
                              (num_time_windows - 1)) - 1) / time_rate for i in
                              range(num_time_windows)], 1, axis=0)
    population_time[0] = 1
    return population_time

# %% ../nbs/data_generation.ipynb 5
def simulate_scenario(population_size: Union[list, np.ndarray],
                      population_time: Union[list, np.ndarray],
                      mutation_rate: float,
                      recombination_rate: float,
                      segment_length: float,
                      num_sample:int,
                      num_replicates: int,
                      seed: int = 69420,
                      model = None,
                     ):

    """ Simulates tree sequence with msprime given population size changes at specific time-points.
    Piece-wise constant simualtion of demography.
    
    :return: generator of tskit.trees.TreeSequence
    """

    demography=msprime.Demography()
    demography.add_population(initial_size=(population_size[0]))
    for i, (time, size) in enumerate(zip(population_time, population_size)):
        if i != 0:
            demography.add_population_parameters_change(time=time, initial_size=size)

    tss = msprime.sim_ancestry(samples=num_sample, recombination_rate=recombination_rate,
                                          sequence_length=int(segment_length), demography=demography,
                                          ploidy=1, model=model, num_replicates=num_replicates, random_seed=seed)

    return tss

# %% ../nbs/data_generation.ipynb 6
def sample_parameters(num_time_windows = 60,
                      n_min = 10_000,
                      n_max = 10_000_000,
                      recombination_rates = [1e-8, 1e-8],
                      population_size: list[float] = None,
                      model = None,
                      
                      ) -> pd.DataFrame:
    

    parameter_names = ["recombination_rate"]
    for i in range(num_time_windows):
        parameter_names.append("pop_size_" + str(i))
    parameter_names.append("model")
    parameters = []
    recombination_rate = np.random.uniform(low=recombination_rates[0], high=recombination_rates[1])

    if population_size is None:
        population_size = sample_population_size(n_min=n_min, n_max=n_max, num_time_windows=num_time_windows)
    
    parameter = [recombination_rate]
    for current_population_size in population_size: 
        parameter.append(current_population_size)
    parameter.append(model)
    parameters.append( parameter )
    parameters = pd.DataFrame(parameters, columns=parameter_names)
    
    return parameters

# %% ../nbs/data_generation.ipynb 7
def sample_population_size(n_min:int=10, n_max:int=100_000, num_time_windows=21) -> list[float]:
    
    """Creates random demography. Function taken from: 
    https://gitlab.inria.fr/ml_genetics/public/dlpopsize_paper
    
    :param int n_min: Lower-bound of demography.
    :param int n_max: Upper-bound of demography.
    :param int num_time_windows: Number of population sizes in demography.
    :return list: 
    """
    
    n_min_log10 = np.log10(n_min)
    n_max_log10 = np.log10(n_max)
    population_size = [10 ** np.random.uniform(low=n_min_log10, high=n_max_log10)] 
    for j in range(num_time_windows - 1):
        population_size.append(10 ** n_min_log10 - 1)
        while population_size[-1] > 10 ** n_max_log10 or population_size[-1]  < 10 ** n_min_log10:
            population_size[-1] = population_size[-2] * 10 ** np.random.uniform(-1, 1)
            
    return population_size

# %% ../nbs/data_generation.ipynb 8
def sample_smooth_population_parameters():

    upper_out_of_bound = lower_out_of_bound = True
    while upper_out_of_bound or lower_out_of_bound:
        steps = 18
        x = np.log(get_population_time(time_rate=0.1, num_time_windows=steps, tmax=10_000_000).tolist())
        y = np.log(sample_population_size(10_000, 10_000_000, steps))
        xnew = np.linspace(x[0], x[-1], num=10000, endpoint=True)
        f_cubic = interp1d(x, y, kind='cubic')
        ynew = f_cubic(xnew)
        upper_out_of_bound = np.sum(np.exp(ynew) > 10_000_000) > 0
        lower_out_of_bound = np.sum(np.exp(ynew) < 10_000) > 0
        x_sample = xnew[np.linspace(10, 9999, 60).astype(int)]
        y_sample = ynew[np.linspace(10, 9999, 60).astype(int)]
        population_time = np.exp(x_sample)
        population_size = np.exp(y_sample)
        
    return population_time, population_size

# %% ../nbs/data_generation.ipynb 9
def simulate_tree_sequence(parameters: pd.DataFrame,
                           population_time: list, 
                           segment_length = 1e6, 
                           num_sample = 10, 
                           num_replicates = 100,
                           seed = 69420,
                          ) -> list[tskit.trees.TreeSequence]:
    
    tree_sequences = []
    population_size = parameters.loc["pop_size_0":"pop_size_" + str(len(population_time)-1)].tolist()
    recombination_rate = parameters.loc["recombination_rate"]
    model = parameters.loc["model"]
    
    if type(model) == np.float64:
        model = msprime.BetaCoalescent(alpha=model)
    else:
        model = None
        

    tree_sequences = simulate_scenario(population_size=population_size,
                    population_time=population_time,
                    mutation_rate=0, # otherwise memory not sufficient
                    recombination_rate=recombination_rate,
                    segment_length=segment_length,
                    num_sample=num_sample,
                    num_replicates=num_replicates,
                    seed=seed, model=model)
        
        
    tss = []
    for ts in tree_sequences:
        tss.append(ts)    
        
    return tss

# %% ../nbs/data_generation.ipynb 10
def generate_sample(nth_scenario):
    
    sequence_length = 1_000_000
    alpha = np.round(np.random.uniform(1.01, 1.99), 2)
    population_time , population_size = sample_smooth_population_parameters()
   
    parameter_set = sample_parameters(
       num_time_windows=60,
       n_min = 10_000,
       n_max = 10_000_000,
       recombination_rates=[1e-8, 1e-8],
       population_size=population_size,
       model=alpha   
    )

    ts = simulate_tree_sequence(
        parameter_set.iloc[0],
        population_time=population_time,
        segment_length=sequence_length,
        num_replicates=num_replicates, 
        seed=nth_scenario+1*1000,
    )[0]

    while ts.num_trees < 500:
        sequence_length = sequence_length * 1.2
        ts = simulate_tree_sequence(
            parameter_set.iloc[0],
            population_time=population_time,
            segment_length=sequence_length,
            num_replicates=num_replicates, 
            seed=nth_scenario+1*1000,
        )[0]

    return ts, population_size, alpha

# %% ../nbs/data_generation.ipynb 11
def alternative_coalescent_mask(ts, population_time, x_times_std=2, n_trees=500):
    
    trees = ts.aslist()[0:n_trees]
    nodes_n_trees = []
    for tree in trees:
        nodes_n_trees += list(tree.nodes())
    
    node_times = [ts.get_time(node.id) for node in ts.nodes() if node.id >= ts.num_samples and node.id in nodes_n_trees]
    
    log_node_times = np.log(node_times)
    mean = log_node_times.mean()
    std = log_node_times.std()
    lowerbound = np.exp(mean-x_times_std*std)
    upperbound = np.exp(mean+x_times_std*std)
    mask1 = population_time > lowerbound
    mask2 = population_time < upperbound
    mask = np.logical_and(mask1, mask2)
    return mask