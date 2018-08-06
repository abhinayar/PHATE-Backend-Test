import sys
import phate_io

phate_io.run_phate_from_file(
    "test_small.csv",
    sparse=True,
    gene_names=True,
    cell_names=True,
    cell_axis='row',
    min_library_size=10,
    min_cells_per_gene=2,
    operator_filename="operator.pickle",
    pca_filename="pca.pickle",
    coords_filename="phate.mat")

phate_io.extract_gene_data(
    gene_id=15,
    pca_filename="pca.pickle",
    color_filename="color.mat")

# change an easy to change parameter
phate_io.run_phate_from_preloaded(
    operator_filename="operator.pickle",
    pca_filename="pca.pickle",
    coords_filename="phate.mat",
    t=12
)

# change a hard-to-change parameter
phate_io.run_phate_from_preloaded(
    operator_filename="operator.pickle",
    pca_filename="pca.pickle",
    coords_filename="phate.mat",
    k=4, a=100
)

sys.stdout.write("OUT DATA TEST SUCCESSFUL")

exit(1)