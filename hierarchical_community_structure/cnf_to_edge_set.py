def read_file(file):
	f=open("{0}".format(file),"r")
	#skip lines until header
	line = f.readline()
	line = line.split(" ")
	while line[0] != 'p' or line[1] != 'cnf':
		line = f.readline()
		line = line.split(" ")
	n = int(line[2])
	m = int(line[3])
	#store clauses in a list
	clauses=[]
	line = f.readline()
	while line:
	    l = line.split(" ")
	    clauses.append(l[0:-1])
	    line = f.readline()
	f.close()
	return clauses, m, n


def cnf_to_edge_set(clauses):
	edge_list = []
	for clause in clauses:
		for i in range(len(clause)-1):
			for j in range(i+1, len(clause)):
				edge_list.append([abs(int(clause[i]))-1, abs(int(clause[j]))-1])
	edge_set = set(map(frozenset, edge_list))
	return edge_set

# import itertools










