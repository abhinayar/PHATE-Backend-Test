import matplotlib
matplotlib.use("Agg")
import os
import scprep
import phate
import pickle
import numpy as np
import scipy.io
import scipy.sparse
from sklearn import decomposition


def _run_phate(phate_op,
               data,
               store_n_pca=20,
               store_dtype=np.float16,
               operator_filename="operator.pickle",
               pca_filename="pca.pickle",
               coords_filename="phate.mat"):
    phate_data = phate_op.fit_transform(data)

    # save phate operator
    del phate_op.X
    del phate_op.graph.data
    with open(operator_filename, 'wb') as handle:
        pickle.dump(phate_op, handle, protocol=pickle.HIGHEST_PROTOCOL)

    # save pca of raw data
    pca = dict()
    try:
        pca['loadings'] = phate_op.graph.data_nu[
            :, :store_n_pca].astype(store_dtype)
        pca['components'] = phate_op.graph.data_pca.components_[
            :store_n_pca, :].astype(store_dtype)
        if not scipy.sparse.issparse(data):
            pca['mean'] = phate_op.graph.data_pca.mean_.astype(store_dtype)
    except AttributeError:
        # no pca performed
        if data.shape[1] > store_n_pca:
            if scipy.sparse.issparse(data):
                pca_op = decomposition.TruncatedSVD(store_n_pca)
            else:
                pca_op = decomposition.PCA(store_n_pca)
            pca['loadings'] = pca_op.fit_transform(data).astype(store_dtype)
            pca['components'] = pca_op.components_.astype(store_dtype)
            if scipy.sparse.issparse(data):
                pca['mean'] = pca_op.mean_.astype(store_dtype)
        else:
            pca['loadings'] = data.astype(store_dtype)
    with open(pca_filename, 'wb') as handle:
        pickle.dump(pca, handle, protocol=pickle.HIGHEST_PROTOCOL)

    # save phate coords
    scipy.io.savemat(coords_filename, {
                     'phate': phate_data.astype(store_dtype)})

    return coords_filename, pca_filename, operator_filename


def run_phate_from_file(
        filename,
        # data loading params
        sparse=True,
        gene_names=None,
        cell_names=None,
        cell_axis=None,
        delimiter=None,
        gene_labels=None,
        allow_duplicates=None,
        genome=None,
        metadata_channels=None,
        # filtering params
        min_library_size=2000,
        min_cells_per_gene=10,
        # normalization params
        library_size_normalize=True,
        transform='sqrt',
        pseudocount=None,
        cofactor=None,
        # saving params
        store_n_pca=20,
        store_dtype=np.float16,
        operator_filename="operator.pickle",
        pca_filename="pca.pickle",
        coords_filename="phate.mat",
        **phate_kws):
    """Run PHATE on a file
    Parameters
    ----------
    filename : str
        Allowed types: csv, tsv, mtx, hdf5/h5 (10X format),
        directory/zip (10X format)
    sparse : bool (recommended: True for scRNAseq, False for CyTOF)
        Force data sparsity. If `None`, sparsity is determined by data type.
    gene_names : str, list or bool
        Allowed values:
        - if filetype is csv or fcs, `True` says gene names are data
        headers, `str` gives a path to a separate csv or tsv file containing
        gene names, list gives an array of gene names, `False` means
        no gene names are given
        - if filetype is mtx, `str` gives a path to a separate csv or tsv file
        containing gene names, list gives an array of gene names, or `False`
        means no gene names are given
        - if filetype is hdf5, h5, directory or zip, must be `None`.
    cell_names : str, list or bool
        Allowed values:
        - if filetype is csv or fcs, `True` says cell names are data
        headers, `str` gives a path to a separate csv or tsv file containing
        cell names, list gives an array of cell names, `False` means
        no cell names are given
        - if filetype is mtx, `str` gives a path to a separate csv or tsv file
        containing cell names, list gives an array of cell names, or `False`
        means no gene names are given
        - if filetype is hdf5, h5, directory or zip, must be `None`.
    cell_axis : {'row', 'column'}
        States whether cells are on rows or columns. If cell_axis=='row',
        data is of shape [n_cells, n_genes]. If cell_axis=='column', data is of
        shape [n_genes, n_cells]. Only valid for filetype mtx and csv
    gene_labels : {'symbol', 'id', 'both'}
        Choice of gene labels for 10X data. Recommended: 'both'
        Only valid for directory, zip, hdf5, h5
    allow_duplicates : bool
        Allow duplicate gene names in 10X data. Recommended: True
        Only valid for directory, zip, hdf5, h5
    genome : str
        Genome name. Only valid for hdf5, h5
    metadata_channels : list of str (recommended: ['Time', 'Event_length', 'DNA1', 'DNA2', 'Cisplatin', 'beadDist', 'bead1'])
        Names of channels in fcs data which are not real measurements.
        Only valid if datatype is fcs.
    min_library_size : int or `None`, optional (default: 2000)
        Cutoff for library size normalization. If `None`,
        library size filtering is not used
    min_cells_per_gene : int or `None`, optional (default: 10)
        Minimum non-zero cells for a gene to be used. If `None`,
        genes are not removed
    library_size_normalize : `bool`, optional (default: True)
        Use library size normalization
    transform : {'sqrt', 'log', 'arcsinh', None}
        How to transform the data. If `None`, no transformation is done
    pseudocount : float (recommended: 1)
        Number of pseudocounts to add to genes prior to log transformation
    cofactor : float (recommended: 5)
        Factor by which to divide genes prior to arcsinh transformation
    **phate_kws : keyword arguments for PHATE
    """
    # check arguments
    if os.path.isdir(filename):
        filetype = 'dir'
    elif os.path.isfile(filename):
        filetype = filename.split('.')[-1]
        if filetype == 'gz':
            filetype = ".".join(filename.split('.')[-2:])
    else:
        raise RuntimeError("file {} not found".format(filename))

    load_args = ['gene_names', 'cell_names', 'cell_axis', 'delimiter',
                 'sparse', 'gene_labels', 'allow_duplicates',
                 'metadata_channels']
    if filetype == 'zip':
        load_fn = scprep.io.load_10X_zip
        load_kws = {'sparse': sparse,
                    'gene_labels': gene_labels,
                    'allow_duplicates': allow_duplicates}
    elif filetype == 'dir':
        load_fn = scprep.io.load_10X
        load_kws = {'sparse': sparse,
                    'gene_labels': gene_labels,
                    'allow_duplicates': allow_duplicates}
    elif filetype in ['hdf5', 'h5']:
        load_fn = scprep.io.load_10X_HDF5
        load_kws = {'sparse': sparse,
                    'gene_labels': gene_labels,
                    'allow_duplicates': allow_duplicates,
                    'genome': genome}
    elif filetype in ['tsv', 'tsv.gz']:
        load_fn = scprep.io.load_tsv
        load_kws = {'sparse': sparse,
                    'gene_names': gene_names,
                    'cell_names': cell_names,
                    'cell_axis': cell_axis}
    elif filetype in ['csv', 'csv.gz']:
        print("Received CSV")
        load_fn = scprep.io.load_csv
        load_kws = {'sparse': sparse,
                    'gene_names': gene_names,
                    'cell_names': cell_names,
                    'cell_axis': cell_axis}
    elif filetype == 'mtx':
        load_fn = scprep.io.load_mtx
        load_kws = {'sparse': sparse,
                    'gene_names': gene_names,
                    'cell_names': cell_names,
                    'cell_axis': cell_axis}
    elif filetype == 'fcs':
        load_fn = scprep.io.load_fcs
        load_kws = {'sparse': sparse,
                    'gene_names': gene_names,
                    'cell_names': cell_names,
                    'metadata_channels': metadata_channels}
    else:
        raise RuntimeError("filetype {} not recognized. Expected 'csv', "
                           "'tsv', 'csv.gz', 'tsv.gz', 'mtx', 'zip', 'hdf5', "
                           "'h5', 'fcs' or a "
                           "directory".format(filetype))
    for arg in load_args:
        if arg == 'sparse':
            # allow None
            pass
        elif arg in load_kws:
            assert eval(arg) is not None, \
                "Expected {} not None for filetype {}".format(arg, filetype)
        else:
            assert eval(arg) is None, \
                "Expected {} to be None for filetype {}. Got {}".format(
                    arg, filetype, eval(arg))

    transform_args = ['pseudocount', 'cofactor']
    if transform == 'sqrt':
        transform_fn = scprep.transform.sqrt
        transform_kws = {}
    elif transform == 'log':
        transform_fn = scprep.transform.log
        transform_kws = {'cofactor': cofactor}
    elif transform == 'arcsinh':
        transform_fn = scprep.transform.arcsinh
        transform_kws = {'pseudocount': pseudocount}
    elif transform is None:
        transform_kws = {}
    else:
        raise RuntimeError("transformation {} not recognized. "
                           "Choose from ['sqrt', 'log', 'arcsinh', "
                           "None]".format(transform))
    for arg in transform_args:
        if arg in transform_kws:
            assert eval(arg) is not None, \
                "Expected {} not None for {} transformation".format(
                    arg, transform)
        else:
            assert eval(arg) is None, \
                "Expected {} to be None for {} transformation. Got {}".format(
                    arg, transform, eval(arg))

    data = load_fn(filename, **load_kws)
    data = scprep.sanitize.check_numeric(data, copy=True)
    if min_library_size is not None:
        data = scprep.filter.filter_library_size(data,
                                                 cutoff=min_library_size)
    if min_cells_per_gene is not None:
        data = scprep.filter.remove_rare_genes(data,
                                               cutoff=min_cells_per_gene)
    if library_size_normalize:
        data = scprep.normalize.library_size_normalize(data)
    if transform is not None:
        data = transform_fn(data, **transform_kws)

    phate_op = phate.PHATE(**phate_kws)
    return _run_phate(phate_op, data,
                      store_n_pca=store_n_pca,
                      store_dtype=store_dtype,
                      operator_filename=operator_filename,
                      pca_filename=pca_filename,
                      coords_filename=coords_filename)


def run_phate_from_preloaded(
        operator_filename="operator.pickle",
        store_n_pca=20,
        store_dtype=np.float16,
        pca_filename="pca.pickle",
        coords_filename="phate.mat",
        **phate_kws):
    # load the operator
    with open(operator_filename, 'rb') as handle:
        phate_op = pickle.load(handle)
    # fix missing `data` component
    phate_op.X = phate_op.graph.data = phate_op.graph.data_nu
    # update parameters
    phate_op.set_params(**phate_kws)
    return _run_phate(phate_op, phate_op.X,
                      store_n_pca=store_n_pca,
                      store_dtype=store_dtype,
                      operator_filename=operator_filename,
                      pca_filename=pca_filename,
                      coords_filename=coords_filename)


def extract_gene_data(gene_id,
                      pca_filename="pca.pickle",
                      color_filename="color.mat"):
    # load pca
    with open(pca_filename, 'rb') as handle:
        pca = pickle.load(handle)

    # inverse pca
    gene_data = pca['loadings']
    if 'components' in pca:
        gene_data = gene_data.dot(pca['components'][:, gene_id])
    else:
        gene_data = gene_data[:, gene_id]
    if 'mean' in pca:
        gene_data = gene_data + pca['mean'][gene_id]

    # save to mat file
    scipy.io.savemat(color_filename, {'color': gene_data})
    return color_filename