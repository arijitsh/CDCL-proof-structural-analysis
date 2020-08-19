#include <algorithm>
#include <assert.h>
#include <cmath>
#include <fstream>
#include <functional>
#include <iostream>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#define OPTION_ALL 'a'
#define OPTION_CVR 'c'
#define OPTION_DEGREE_VECTOR 'd'
#define OPTION_RESOLVABILITY 'r'

#define MSV_NUM_BUCKETS 10
#define MAX_MERGEABILITY_SCORE 0.5
#define MAX_MERGEABILITY_SCORE_INV 2

// Global options
std::set<char> options;

// Read clauses from file
static int readClauses(std::vector<std::vector<long long>>& clauses, long long& numVars, long long& numClauses, long long& maxClauseWidth, const std::string& inputFileStr) {
	std::ifstream file(inputFileStr);
	if (!file.is_open()) {
		std::cerr << "Error while opening: " << inputFileStr << std::endl;
		return 1;
	}

	// Read CNF header
	bool gotHeader = false;
	std::string lineStr;
	while (!gotHeader) {
		std::getline(file, lineStr);
		if (file.bad()) return 1;
		if (lineStr.size() == 0) continue; // Skip empty lines

		std::stringstream line(lineStr);
		char firstChar = 0;
		line >> firstChar; if (line.bad()) return 1;
		if (firstChar == 'c') continue;	// Skip comments
		if (firstChar != 'p') {
			std::cerr << "Invalid header line" << std::endl;
			return 1;
		}

		std::string cnfString;
		line >> cnfString; if (line.bad()) return 1;
		if (cnfString != "cnf") {
			std::cerr << "Invalid header line" << std::endl;
		}
		line >> numVars >> numClauses; if (line.bad()) return 1;
		gotHeader = true;
	}

	// Reserve memory
	clauses.reserve(numClauses);

	// Read clauses
	std::vector<long long> clause;
	while (std::getline(file, lineStr)) {
		if (lineStr.size() == 0) continue; // Skip empty lines
	
		std::stringstream line(lineStr);
		long long var = 0;
		while (line.good()) {
			line >> var; if (line.bad()) return 1;
			if (var == 0) { // Clauses end upon reading zero
				clauses.push_back(clause);
				maxClauseWidth = std::max(maxClauseWidth, static_cast<long long>(clause.size()));
				clause.clear();
			} else {
				clause.push_back(var);
			}
		}
	}
	return 0;
}

static void computeCVR(double& cvr, long long numClauses, long long numVars) {
	cvr = numClauses / static_cast<double>(numVars);
}

// Optimizing resolvability computation
// O((max_degree(v))^2 k^2 log(k) + (m k)) 
static int computeResolvable(
	std::pair<long long, long long>& numResMerge, std::pair<double, double>& mergeabilityScore, std::vector<long long>& mergeabilityVector,
	std::vector<long long>& mergeabilityScoreVector, std::pair<long long, long long>& totalClauseWidths,
	std::vector<std::vector<long long>>& clauses, long long numVariables
) {
	// Generate clause lookup table
	// O(m k)
	std::vector<std::vector<unsigned int>> posClauseIndices(numVariables);
	std::vector<std::vector<unsigned int>> negClauseIndices(numVariables);
	for (unsigned int i = 0; i < clauses.size(); ++i) {
		for (unsigned int c_i = 0; c_i < clauses[i].size(); ++c_i) {
			const int var = clauses[i][c_i];
			if (var > 0) { // The variable should never be zero
				posClauseIndices[+var - 1].emplace_back(i);	
			} else {
				negClauseIndices[-var - 1].emplace_back(i);
			}
		}

		// Add to total clause width
		totalClauseWidths.first += static_cast<long long>(clauses[i].size());
	}

	// Find all clauses which resolve on a variable
	// O((max_degree(v))^2 k^2 log(k))
	for (long long i = 0; i < numVariables; ++i) {
		const std::vector<unsigned int>& posClauses = posClauseIndices[i];
		const std::vector<unsigned int>& negClauses = negClauseIndices[i];
		
		// Check for clauses which resolve on the variable
		// O((max_degree(v))^2 k log(k))
		for (unsigned int c_i : posClauses) {
			const std::vector<long long>& posClause = clauses[c_i];

			// Initialize set for checking resolvability
			// O(k log(k))
			std::set<long long> found;
			for (long long var : posClause) {
				found.insert(var);
			}

			// Check if any of the negative clause resolves with the positive clause
			// O((max_degree(v)) k log(k))
			for (unsigned int c_j : negClauses) {
				const std::vector<long long>& negClause = clauses[c_j];

				// Check for resolvable/mergeable clauses
				// O(k log(k))
				bool resolvable = false; // True if there is exactly one opposing literal
				long long tmpNumMergeable = 0;
				for (unsigned int k = 0; k < negClause.size(); ++k) {
					if (found.find(-negClause[k]) != found.end()) {
						if (resolvable) {
							resolvable = false;
							break;
						}
						resolvable = true;
					} else if (found.find(negClause[k]) != found.end()) {
						++tmpNumMergeable;
					}
				}

				// Update counts
				// O(1)
				if (resolvable) {
					++numResMerge.first;
					++mergeabilityVector[tmpNumMergeable];
					numResMerge.second += tmpNumMergeable;

					// Calculate normalized mergeability score
					const int totalClauseSize = static_cast<int>(posClause.size() + negClause.size());
					if (totalClauseSize > 2) {
						const double tmpMergeabilityScore  = tmpNumMergeable / static_cast<double>(totalClauseSize - 2);
						const double tmpMergeabilityScore2 = tmpNumMergeable / static_cast<double>(totalClauseSize - tmpNumMergeable - 2);
						mergeabilityScore.first  += tmpMergeabilityScore;
						mergeabilityScore.second += tmpMergeabilityScore2;

						// Add to histogram
						// index = [ (local mergeability score) / (max mergeability score) ] * (num buckets)
						const int scoreVectorIndex = static_cast<int>(std::floor(MAX_MERGEABILITY_SCORE_INV * MSV_NUM_BUCKETS * tmpMergeabilityScore));
						++mergeabilityScoreVector[scoreVectorIndex];
					}

					// Add to total post-resolution clause size
					const long long postResolutionClauseSize = static_cast<long long>(totalClauseSize - tmpNumMergeable - 2);
					totalClauseWidths.second += static_cast<long long>(postResolutionClauseSize);
				}
			}
		}
	}

	return 0;
} 

static int computeDegreeVector(std::vector<long long>& degreeVector, std::vector<std::vector<long long>>& clauses) {
	// Iterate through every variable of every clause
	for (const std::vector<long long>& clause : clauses) {
		for (long long x : clause) {
			// Increment corresponding variable in degree vector
			++degreeVector[std::abs(x) - 1];
		}
	}

	std::sort(degreeVector.rbegin(), degreeVector.rend());

	return 0;
}

static int writeFile(const std::string& outputFileStr, std::function<void(std::ofstream&)> writerFunc) {
	std::ofstream outputFile(outputFileStr);
	if (!outputFile.is_open()) {
		std::cerr << "Error while opening: " << outputFileStr << std::endl;
		return 1;
	}

	writerFunc(outputFile);
	if (outputFile.bad()) {
		std::cerr << "Error while writing: " << outputFileStr << std::endl;
		return 1;
	}

	return 0;
}

static void writeCVR(std::ofstream& outFile, long long numClauses, long long numVars, double cvr) {
	outFile << numClauses << " " << numVars << " " << cvr << std::endl;
}

static void writeResolvability(std::ofstream& outFile, long long numResolvable, long long numMergeable, const std::pair<double, double>& mergeabilityScore) {
	outFile << numResolvable << " " << numMergeable << " " << mergeabilityScore.first << " " << mergeabilityScore.second << std::endl;
}

static void writeDegreeVector(std::ofstream& outFile, std::vector<long long>& degreeVector) {
	for (unsigned int i = 0; i < degreeVector.size(); ++i) {
		outFile << i + 1 << " " << degreeVector[i] << std::endl;
	}
}

static void writeMergeabilityVector(std::ofstream& outFile, std::vector<long long>& mergeabilityVector) {
	// Determine when to stop outputting the mergeability vector
	unsigned int indexOfGreatestNonZero = 0;
	for (unsigned int i = 0; i < mergeabilityVector.size(); ++i) {
		if (mergeabilityVector[i] != 0) indexOfGreatestNonZero = i;
	}

	// Output mergeability vector (output an additional zero at the end)
	for (unsigned int i = 0; i <= indexOfGreatestNonZero + 1; ++i) {
		outFile << i << " " << mergeabilityVector[i] << std::endl;
	}
}

static void writeMergeabilityScoreVector(std::ofstream& outFile, std::vector<long long>& mergeabilityScoreVector) {
	for (int i = 0; i <= MSV_NUM_BUCKETS; ++i) {
		outFile << (i * MAX_MERGEABILITY_SCORE) / static_cast<double>(MSV_NUM_BUCKETS) << " " << mergeabilityScoreVector[i] << std::endl;
	}
}

static void writeClauseWidths(std::ofstream& outFile, long long totalOriginalClauseWidth, long long totalPostResClauseWidth) {
	outFile << totalOriginalClauseWidth << " " << totalPostResClauseWidth << std::endl;
}

static void printHelp(const char* command) {
	std::cerr << "Usage: " << command << " <OPTION [OPTIONS...]> <INPUT [INPUTS...]>" << std::endl;
	std::cerr << "\t-" << OPTION_ALL           << ": enable all computations" << std::endl;
	std::cerr << "\t-" << OPTION_CVR           << ": compute CVR" << std::endl;
	std::cerr << "\t-" << OPTION_DEGREE_VECTOR << ": compute degree vector" << std::endl;
	std::cerr << "\t-" << OPTION_RESOLVABILITY << ": compute resolvability, mergeability, mergeability vector, and total clause widths" << std::endl;
}

static int parseInput(std::set<char>& options, std::vector<std::string>& inputFiles, const int argc, const char* const* argv) {
	// Read in option flags and input files
	for (int argIndex = 1; argIndex < argc; ++argIndex) {
		std::string inputStr(argv[argIndex]);
		if (inputStr[0] == '-') { // Value is option
			for (unsigned int i = 1; i < inputStr.size(); ++i) {
				switch (inputStr[i]) {
					case OPTION_ALL:
					case OPTION_CVR:
					case OPTION_DEGREE_VECTOR:
					case OPTION_RESOLVABILITY:
						options.insert(inputStr[i]);
						break;
					default: return 1;
				}
			}
		} else { // Value is input file
			inputFiles.push_back(inputStr);
		}
	}

	// Enable all options if OPTION_ALL is enabled
	if (options.find(OPTION_ALL) != options.end()) {
		options.insert(OPTION_CVR);
		options.insert(OPTION_DEGREE_VECTOR);
		options.insert(OPTION_RESOLVABILITY);
	}

	// Report an error if there are no options
	return options.size() == 0;
}

using namespace std::placeholders;
int main (const int argc, const char* const * argv) {
	// Validate input
	if (argc < 2) {
		printHelp(argv[0]);
		return 1;
	}

	// Parse input
	std::vector<std::string> inputFiles;
	if (parseInput(options, inputFiles, argc, argv)) {
		printHelp(argv[0]);
		return 1;
	}

	for (const std::string& inputFileStr : inputFiles) {
		// Read clauses from file
		static const std::string CNF_EXTENSION = ".cnf";
		const std::string inputFileBaseStr = inputFileStr.substr(0, inputFileStr.size() - CNF_EXTENSION.size());
		long long numVars = 0, numClauses = 0, maxClauseWidth = 0;
		std::vector<std::vector<long long>> clauses;
		if (readClauses(clauses, numVars, numClauses, maxClauseWidth, inputFileStr)) return 1;
		assert(numVars > 0);
		assert(numClauses > 0);
		assert(maxClauseWidth > 0);

		// Calculate and output CVR
		if (options.find(OPTION_CVR) != options.end()) {
			double cvr = 0;
			computeCVR(cvr, numClauses, numVars);
			assert(cvr > 0);
			writeFile(inputFileBaseStr + ".cvr", std::bind(writeCVR, _1, numClauses, numVars, cvr));
		}

		// Calculate and output degree vector
		if (options.find(OPTION_DEGREE_VECTOR) != options.end()) {
			std::vector<long long> degreeVector(numVars);
			computeDegreeVector(degreeVector, clauses);
			writeFile(inputFileBaseStr + ".dv", std::bind(writeDegreeVector, _1, degreeVector));
		}

		// Calculate and output num resolvable and num mergeable
		if (options.find(OPTION_RESOLVABILITY) != options.end()) {
			std::pair<double, double> mergeabilityScore = std::make_pair<double, double>(0, 0);
			std::pair<long long, long long> numResMerge = std::make_pair<long long, long long>(0, 0);
			std::vector<long long> mergeabilityVector(maxClauseWidth + 1);
			std::vector<long long> mergeabilityScoreVector(MSV_NUM_BUCKETS + 1);
			std::pair<long long, long long> totalClauseWidths = std::make_pair<long long, long long>(0, 0);
			computeResolvable(numResMerge, mergeabilityScore, mergeabilityVector, mergeabilityScoreVector, totalClauseWidths, clauses, numVars);
			assert(numResMerge.first  >= 0);
			assert(numResMerge.second >= 0);

			writeFile(inputFileBaseStr + ".tcw", std::bind(writeClauseWidths, _1, totalClauseWidths.first, totalClauseWidths.second));
			writeFile(inputFileBaseStr + ".rvm", std::bind(writeResolvability, _1, numResMerge.first, numResMerge.second, mergeabilityScore));
			writeFile(inputFileBaseStr + ".mv",  std::bind(writeMergeabilityVector, _1, mergeabilityVector));
			writeFile(inputFileBaseStr + ".msv", std::bind(writeMergeabilityScoreVector, _1, mergeabilityScoreVector));
		}
	}

	return 0;
}
