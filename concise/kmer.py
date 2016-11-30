import pandas as pd
import itertools
from glmnet import ElasticNet
from sklearn.feature_selection import f_regression
from scipy.sparse import csc_matrix
# csv_file_path = "../data/pombe_half-life_UTR3.csv"
# dt = pd.read_csv(csv_file_path)
# dt["seq"].str.count("ATG")

# seq_series = dt["seq"]
# t = time.process_time()
# a = kmer_count_2(seq_series, 3)
# elapsed_time = time.process_time() - t
# print(elapsed_time)

# seq_series = dt["seq"]
# t = time.process_time()
# b = kmer_count(seq_series, 3)
# elapsed_time = time.process_time() - t
# print(elapsed_time)


# def kmer_count_2(seq_series, k):
#     # generate all k-mers
#     all_kmers = generate_all_kmers(k)
#     kmer_count_list = []
#     return pd.concat([seq_series.str.count(kmer) for kmer in all_kmers], axis = 1, keys = all_kmers)

# TODO - get feature selection working
# csv_file_path = "../data/pombe_half-life_UTR3.csv"
# dt = pd.read_csv(csv_file_path)
# response = 'hlt'
# sequence = 'seq'
# best = best_kmers(dt, response, sequence, k = 6, consider_shift = True, n_cores = 1)

def hamming_distance(s1, s2):
    """Return the Hamming distance between equal-length sequences"""
    if len(s1) != len(s2):
        raise ValueError("Undefined for sequences of unequal length")
    return sum(el1 != el2 for el1, el2 in zip(s1, s2))

def best_kmers(dt, response, sequence, k = 6, consider_shift = True, n_cores = 1):
    """
    Find best k-mers for CONCISE initialization.
    
    Args:
        dt (pd.DataFrame): Table containing response variable and sequence.
        response (str): Name of the column used as the reponse variable.
        sequence (str): Name of the column storing the DNA/RNA sequences.
        k (int): Desired k-mer length.
        n_cores (int): Number of cores to use for computation. It can use up to 3 cores.
        consider_shift (boolean): When performing stepwise k-mer selection. Is TATTTA similar to ATTTAG?
    Returns:
        string list: Best set of motifs for this dataset sorted with respect to
                     confidence (best candidate occuring first).


    Details:
        First a lasso model gets fitted to get a set of initial motifs. Next, the best
        subset of unrelated motifs is selected by stepwise selection.
    """
    y = dt[response]
    seq = dt[sequence]
    dt_kmer = kmer_count(seq, k)
    Xsp = csc_matrix(dt_kmer)
    en = ElasticNet(alpha = 1, standardize=False, n_folds = 3)
    en.fit(Xsp, y)
    # which coefficients are nonzero?=
    nonzero_kmers = dt_kmer.columns.values[en.coef_ != 0].tolist()

    # perform stepwise selection

    # largest number of motifs where they don't differ by more than 1 k-mer
    def find_next_best(dt_kmer, y, selected_kmers, to_be_selected_kmers, consider_shift = True):
        """
        perform stepwise model selection while preventing to add a motif similar to the
        already selected motifs.
        """
        F, pval = f_regression(dt_kmer[to_be_selected_kmers], y)
        kmer = to_be_selected_kmers.pop(pval.argmin())
        selected_kmers.append(kmer)

        def select_criterion(s1, s2, consider_shift = True):
            if hamming_distance(s1, s2) <= 1:
                return False
            if consider_shift and hamming_distance(s1[1:], s2[:-1]) == 0:
                return False
            if consider_shift and hamming_distance(s1[:-1], s2[1:]) == 0:
                return False
            return True

        to_be_selected_kmers = [ckmer for ckmer in to_be_selected_kmers
                                if select_criterion(ckmer, kmer, consider_shift)]
        if len(to_be_selected_kmers) == 0:
            return selected_kmers
        else:
            return find_next_best(dt_kmer, y, selected_kmers, to_be_selected_kmers, consider_shift)

    selected_kmers = find_next_best(dt_kmer, y, [], nonzero_kmers, consider_shift)

    return selected_kmers


# from sklearn.datasets import load_iris

def kmer_count(seq_list, k):
    """
    Generate k-mer counts from a set of sequences

    Args:
        seq_list (iterable): List of DNA sequences (with letters from {A, C, G, T})
        k (int): K in k-mer.
    Returns:
        pandas.DataFrame: Count matrix for seach sequence in seq_list

    Example:
    >>> kmer_count(["ACGTTAT", "GACGCGA"], 2)
       AA  AC  AG  AT  CA  CC  CG  CT  GA  GC  GG  GT  TA  TC  TG  TT
    0   0   1   0   1   0   0   1   0   0   0   0   1   1   0   0   1
    1   0   1   0   0   0   0   2   0   2   1   0   0   0   0   0   0
    """
    # generate all k-mers
    all_kmers = generate_all_kmers(k)
    kmer_count_list = []
    for seq in seq_list:
        kmer_count_list.append([seq.count(kmer) for kmer in all_kmers])
    return pd.DataFrame(kmer_count_list, columns = all_kmers) 

def generate_all_kmers(k):
    """
    Generate all possible k-mers

    Example:
    >>> generate_all_kmers(2)
    ['AA', 'AC', 'AG', 'AT', 'CA', 'CC', 'CG', 'CT', 'GA', 'GC', 'GG', 'GT', 'TA', 'TC', 'TG', 'TT']
    """
    bases=['A', 'C', 'G', 'T']
    return [''.join(p) for p in itertools.product(bases, repeat=k)]
