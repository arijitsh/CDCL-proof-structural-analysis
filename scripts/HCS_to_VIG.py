from cnf_to_edge_set import cnf_to_edge_set, read_file, cnf_to_clauses_list
import igraph
import sys
import os
import random
import math
import copy

def get_leaf_graph(n):
	edges_to_add = []
	#g = igraph.Graph.Erdos_Renyi(n, 0.3)
	g = igraph.Graph(n)
	g.vs["visited"] = [False] * g.vcount()
	for v in range(g.vcount()):
		if g.vs[v]["visited"] == False:
			(u, w) = random.sample(range(0, g.vcount()), 2)
			while v == u or v == w:
				(u, w) = random.sample(range(0, g.vcount()), 2)
			edges_to_add.append([u, v])
			edges_to_add.append([u, w])
			edges_to_add.append([v, w])
			g.vs[v]["visited"] = True
			g.vs[u]["visited"] = True
			g.vs[w]["visited"] = True
	while len(edges_to_add) < n * 8.8:
		# enforce remaining edges to be in triangles too
		(u, v, w) = random.sample(range(0, g.vcount()), 3)
		edges_to_add.append([u, v])
		edges_to_add.append([u, w])
		edges_to_add.append([v, w])
	g.add_edges(edges_to_add)

	return g

def combine_subgraphs(subgraphs):
	current_vertex_count = 0
	total_vertex_count = 0
	community_id_upper_bounds = []
	combined_disconnected_subgraphs = igraph.Graph()

	for g in subgraphs:
		total_vertex_count += g.vcount()
		community_id_upper_bounds.append(total_vertex_count)

	combined_disconnected_subgraphs.add_vertices(total_vertex_count)

	edges_to_add = []
	for i, g in enumerate(subgraphs):
		for e in g.es:
			edges_to_add.append([current_vertex_count+e.source, current_vertex_count+e.target])
		current_vertex_count = community_id_upper_bounds[i]
	combined_disconnected_subgraphs.add_edges(edges_to_add)

	# At this point, combined_zero_adjacency_matrix is an 
	# all 0 matrix except for the diagonal being the subcommunities to combine
	return combined_disconnected_subgraphs, community_id_upper_bounds

def same_community(u, v, community_id_upper_bounds):
	previous = 0
	for current in community_id_upper_bounds:
		if previous <= u < current and previous <= v < current:
			return True
		previous = current
	return False

def pick_inter_triangle(g, u, random_inter_vars, community_id_upper_bounds):
	v = random.sample(random_inter_vars, 1)[0]
	while same_community(u, v, community_id_upper_bounds):
		v = random.sample(random_inter_vars, 1)[0]
	w = random.sample(random_inter_vars, 1)[0]
	while w == v or w == u:
		w = random.sample(random_inter_vars, 1)[0]
	return v, w


def add_edges_to_combined_disconnected_subgraphs(level, depth, g, inter_vars_fraction, community_id_upper_bounds):

	# randomly pick exactly inter-var number of inter-community variables
	# and add exactly inter-edges number of inter-community edges within the selected variables
	# 	- range(a, b): b is exclusive
	# 	- picking inter_vars distinct variables

	#inter_vars_decay = float(level)/depth
	inter_vars_decay = 1
	inter_vars = int(g.vcount()*inter_vars_fraction * inter_vars_decay)
	#inter_edges = int(inter_vars*math.log(inter_vars)/2)
	inter_edges = int(inter_vars * 3)
	while True:
		# phase 1: for each uncovered vertex, connect it to a vertex in another community
		#print("phase 1 starts")
		inter_edges_count = 0
		# select inter_vars from each community 
		random_inter_vars = []
		start = 0
		end = community_id_upper_bounds[0]
		for i in range(len(community_id_upper_bounds)):
			end = community_id_upper_bounds[i]
			random_inter_vars += random.sample(range(start, end-1), inter_vars/len(community_id_upper_bounds))
			start = end
		#random_inter_vars = random.sample(range(0, g.vcount()), inter_vars)

		uncovered = set(random_inter_vars)
		# TODO: add an array for edges_to_add and add them all at once
		edges_to_add=[]
		while len(uncovered) != 0:
			# u is a random vertex in uncovered
			u = uncovered.pop()
			v, w = pick_inter_triangle(g, u, random_inter_vars, community_id_upper_bounds)
			if g.get_eid(u, v, directed=False, error=False) < 0:
				uncovered.discard(v)
				#g.add_edge(u, v)
				edges_to_add.append([u, v])
				inter_edges_count+=1
			if g.get_eid(u, w, directed=False, error=False) < 0:
				uncovered.discard(w)
				#g.add_edge(u, w)
				edges_to_add.append([u, w])
				inter_edges_count+=1
			if g.get_eid(v, w, directed=False, error=False) < 0:
				uncovered.discard(v)
				uncovered.discard(w)
				#g.add_edge(v, w)
				edges_to_add.append([v, w])
				inter_edges_count+=1
		g.add_edges(edges_to_add)

		# print("phase 1 done")
		# print("phase 2 started")
		# phase 2: randomly assign the remaining edges
		# TODO: instead of randomly picking u and v, we can fix u first and randomly picking a v from a different community
		if inter_edges >= inter_edges_count:
			edges_to_add=[]
			while inter_edges - inter_edges_count > 0:
				u = random.sample(random_inter_vars, 1)[0]
				v, w = pick_inter_triangle(g, u, random_inter_vars, community_id_upper_bounds)
				if g.get_eid(u, v, directed=False, error=False) < 0:
					#g.add_edge(u, v)
					edges_to_add.append([u, v])
					inter_edges_count+=1
				if g.get_eid(u, w, directed=False, error=False) < 0:
					#g.add_edge(u, w)
					edges_to_add.append([u, w])
					inter_edges_count+=1
				if g.get_eid(v, w, directed=False, error=False) < 0:
					#g.add_edge(v, w)
					edges_to_add.append([v, w])
					inter_edges_count+=1
			#print("phase 2 done")
			g.add_edges(edges_to_add)
			break
	return g

def count_inter_vars(g, community_id_upper_bounds):
	inter_vars = set()
	for e in g.es:
		u = e.source
		v = e.target
		if not same_community(u, v, community_id_upper_bounds):
			# sort and binary search?
			inter_vars.add(u)
			inter_vars.add(v)
	return len(inter_vars)

def compute_modularity(g, community_id_upper_bounds):
	membership_list = []
	previous = 0
	community_index = 0
	for current in community_id_upper_bounds:
		for i in range(current - previous):
			membership_list.append(community_index)
		previous = current
		community_index += 1
	return g.modularity(membership_list)

def print_matrix(matrix):
	for i in matrix:
		print(i)
	return

def generate_VIG(level, depth, leaf_community_size, inter_vars_fraction, degree):
	
	if level == depth:
		# change get leaf community to return an igraph object
		#return igraph.Graph.Adjacency(get_leaf_adjacency_matrix(leaf_community_size), mode="UNDIRECTED")
		return get_leaf_graph(leaf_community_size)
	current_degree = degree[level-1]

	subgraphs = []
	for i in range(current_degree):
		subgraphs.append(generate_VIG(level+1, depth, leaf_community_size, inter_vars_fraction, degree))
	
	combined_disconnected_subgraphs, community_id_upper_bounds = combine_subgraphs(subgraphs)

	#iteration = 1
	# start searching for valid matrices 
	#while True:
	# print("level {0}".format(level))
	# we add current_inter_edge number of 1's in the matrix (excluding the diagonal)
	updated_combined_graph = add_edges_to_combined_disconnected_subgraphs(level, depth, combined_disconnected_subgraphs, inter_vars_fraction, community_id_upper_bounds)
	#print("done")
		# 	# check current_modularity
		# 	# switch off checking for modularity
		# 	actual_modularity = compute_modularity(updated_combined_graph, community_id_upper_bounds)
		# 	if abs(current_modularity - actual_modularity) < 0.1:
		# 		break
		#break
		#iteration+=1
	return updated_combined_graph

# have inputs
# need inter_edges > inter_vars*log(inter_vars)/2, log base e.
# experiment 1: fixing the size of graph, vary inter_vars and inter_edges
	# 1.1 fixing inter_vars, scale up inter_edges
	# 1.2 fix inter_edges, scale down inter_vars
# experiment 2: 
# depth = 7
# leaf_community_size = 10
# # let inter_vars be the density (a fraction of total number of vars in the subgraph)
# inter_vars_fraction = 0.3
# degree = [2, 2, 2, 2, 2, 2]
# #modularity = [0.7, 0.6, 0.5, 0.4]


# g = generate_VIG(1, depth, leaf_community_size, inter_vars_fraction, degree)

# layout = g.layout("large")
# visual_style = {}
# visual_style["vertex_size"] = 5
# visual_style["layout"] = layout
# visual_style["bbox"] = (1000, 1000)
# visual_style["margin"] = 10
# vertex_clustering = g.community_multilevel()
# igraph.plot(vertex_clustering, "HCS.svg", mark_groups = True, **visual_style)

#print_matrix(adjacency_matrix)