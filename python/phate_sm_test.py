import sys
import phate_io
import phate
import numpy as np

phate_data, phate_op = phate_io.run_phate_from_file(
    "sample_data.csv",
    sparse=True,
    gene_names=True,
    cell_names=True,
    cell_axis='row',
    min_library_size=10,
    min_cells_per_gene=2,
    operator_filename="operator.pickle",
    pca_filename="pca.pickle",
    coords_filename="phate.mat")

pca_data = phate_op.graph.data_nu[:, :20]
singular_vectors = phate_op.graph.data_pca.components_[:20, :]

gene = "Mpo"
gene_idx = np.argwhere(phate_op.X.columns == gene).flatten()[0]
gene_data = np.dot(pca_data, singular_vectors[:, gene_idx])
phate.plot.scatter2d(phate_data, c=gene_data, legend_title="Mpo",
                     filename="sample_data.png")

sys.stdout.write("OUT DATA TEST SUCCESSFUL")

exit(1)