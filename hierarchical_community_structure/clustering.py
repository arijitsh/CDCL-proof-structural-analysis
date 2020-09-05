import igraph
import sys
from cnf_to_edge_list import cnf_to_edge_list, read_file
import os
import numpy as np
from random import randrange


def rgba(color, percent, opacity):
    '''assumes color is rgb between (0, 0, 0) and (255, 255, 255)'''
    color = np.array(color)
    white = np.array([255, 0, 0])
    vector = white-color
    final_color = color + vector * percent
    rgba = 'rgba(' + str(final_color[0]) + ',' + str(final_color[1]) + ',' + str(final_color[2]) + ',' + str(opacity) + ')'
    return rgba

def create_directory(file):
	directory = os.path.dirname(file)
	filename =  os.path.basename(file)
	name = filename[:-4]
	if directory == '':
		output_directory = name + '/'
	else:
		output_directory = directory + '/' + name + '/'
	if not os.path.isdir(output_directory):
		os.mkdir(output_directory)
	return output_directory

def set_community_structure_style(g):
	layout = g.layout("large")
	visual_style = {}
	visual_style["layout"] = layout
	visual_style["bbox"] = (5000, 5000)
	visual_style["vertex_size"] = 1
	return visual_style

def set_hierarchical_tree_style(hierarchical_tree):
	layout = hierarchical_tree.layout_reingold_tilford(root=[0])
	visual_style = {}
	visual_style["layout"] = layout
	visual_style["bbox"] = (5000, 5000)
	#visual_style["vertex_size"] = hierarchical_tree.vs['vertex_size']
	#visual_style["vertex_color"] = hierarchical_tree.vs['color']
	return visual_style

def plot_community_structure(vertex_clustering, path, output_directory):

	filename = str(len(path) - 1)
	for i in range(len(path)):
		filename+="_"
		filename+=str(path[i])
	filename = filename + ".svg"

	igraph.plot(vertex_clustering, output_directory + filename, mark_groups = True, **community_structure_style)
	return

def plot_hierarchical_tree(hierarchical_tree, file):
	filename = file + ".svg"
	hierarchical_tree_style = set_hierarchical_tree_style(hierarchical_tree)
	igraph.plot(hierarchical_tree, filename, **hierarchical_tree_style)
	return

def create_edge_list_hierarchical_tree(current_node, number_of_children, max_node):
	edge_list = []
	for i in range(number_of_children):
		edge_list.append([current_node, max_node-i])
	return edge_list

def compute_hierarchical_community_structure(g, hierarchical_tree, current_node, path):
	#calculates community structure
	vertex_clustering = g.community_multilevel()
	#vertex_clustering = g.community_edge_betweenness().as_clustering()
	#plot all sub-communities and saving them to files.
	#plot_community_structure(vertex_clustering, path, output_directory)

	percent = (g.modularity(vertex_clustering) + 0.5) / 1.5
	hierarchical_tree.vs[current_node]['color'] = rgba((255, 245, 245), percent, 0.8)
	hierarchical_tree.vs[current_node]['vertex_size'] = 100*percent

	if len(vertex_clustering) > 1:
		#modifying hierarchical community structure tree
		hierarchical_tree.add_vertices(len(vertex_clustering))
		hierarchical_tree.add_edges(create_edge_list_hierarchical_tree(current_node, len(vertex_clustering), hierarchical_tree.vcount()-1))
		current_max_node = hierarchical_tree.vcount()-1

		for c in range(len(vertex_clustering)):
			current_node = current_max_node - c
			temp_path = path[:]
			temp_path.append(c)
			compute_hierarchical_community_structure(vertex_clustering.subgraph(c), hierarchical_tree, current_node, temp_path)
	return

file = sys.argv[1]
print(file)
#output_directory = create_directory(file)
clauses, m, n = read_file(file)
edge_set = cnf_to_edge_list(clauses)
#edge_list = list(cnf_to_edge_list(clauses))
edge_list = [list(e) for e in edge_set]

g = igraph.Graph()
g.add_vertices(n)
g.add_edges(edge_list)
path = [0]

hierarchical_tree = igraph.Graph()
hierarchical_tree.add_vertices(1)
current_node = 0

community_structure_style = set_community_structure_style(g)

#compute_hierarchical_community_structure(g, hierarchical_tree, current_node, path, output_directory)
compute_hierarchical_community_structure(g, hierarchical_tree, current_node, path)
plot_hierarchical_tree(hierarchical_tree, file)