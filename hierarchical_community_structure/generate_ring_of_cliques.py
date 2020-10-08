import sys
# number of cliques
n = int(sys.argv[1])
# size of each clique
k = int(sys.argv[2])

print("p cnf {0} {1}".format(n * k, k))

for i in range(n):
	start = i * k + 1
	end = i * k + k
	#print clauses within a clique
	current = start
	clause = ""
	while current <= end:
		clause += " {0}".format(current)
		current += 1
	clause += " 0"
	print(clause)
	#print edge to connect to the next clique
	if i == n - 1:
		print("{0} {1} 0".format(end, 1))
	else:
		print("{0} {1} 0".format(end, end + 1))

