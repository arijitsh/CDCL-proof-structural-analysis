CWD="$(pwd)"
cd ~
SCRATCH_DIR="$(pwd)/scratch"
cd $CWD

GENERATE_PROOF="true"
SHARCNET_ACCOUNT_NAME="vganesh"
SHARCNET_TIMEOUT="2:00:00"
SHARCNET_MEMORY="2G"

OPTION_GLUCOSE="glucose"
OPTION_DRAT="drat"
OPTION_DEPENDENCY="dependency"
OPTION_GR="gr"

if [[ $# -ne 7 ]]; then
    echo "Usage: $0 <BEGIN_ROUNDS> <END_ROUNDS> <BEGIN_RESTRICTIONS> <END_RESTRICTIONS> <CDCL_REPOSITORY> <OUT_DIRECTORY> <OPTION>"
    echo "Options: \"${OPTION_GLUCOSE}\", \"${OPTION_DRAT}\", \"${OPTION_DEPENDENCY}\", \"${OPTION_GR}\""
    exit 1
fi

BEGIN_ROUNDS=$1
END_ROUNDS=$2
BEGIN_RESTRICTIONS=$3
END_RESTRICTIONS=$4
CDCL_REPOSITORY=$5
OUT_DIRECTORY="${SCRATCH_DIR}/$6"
OPTION=$7

if [[ $END_ROUNDS < $BEGIN_ROUNDS ]]; then
    echo "Cannot begin rounds after the end"
    exit 1
fi

if [[ $END_RESTRICTIONS < $BEGIN_RESTRICTIONS ]]; then
    echo "Cannot begin restrictions after the end"
    exit 1
fi

if [[ $OPTION != $OPTION_GLUCOSE ]] && [[ $OPTION != $OPTION_DRAT ]] && [[ $OPTION != $OPTION_DEPENDENCY ]] && [[ $OPTION != $OPTION_GR ]]; then
    echo "Received invalid option ${OPTION}"
    echo "Options: \"${OPTION_GLUCOSE}\", \"${OPTION_DRAT}\", \"${OPTION_DEPENDENCY}\", \"${OPTION_GR}\""
    exit 1
fi

CRYPTO_EXEC="${CDCL_REPOSITORY}/SAT-encoding/crypto/main"
RESTRICT_EXEC="${CDCL_REPOSITORY}/scripts/crypto/restrictSHA1"
GLUCOSE_EXEC="${CDCL_REPOSITORY}/executables/glucose"
DRAT_EXEC="${CDCL_REPOSITORY}/executables/drat-trim"
GR_EXEC="python ${CDCL_REPOSITORY}/scripts/dependencyToGR.py"

echo
echo "----------------------------------"
echo "CRYPTO_EXEC:     $CRYPTO_EXEC"
echo "RESTRICT_EXEC:   $RESTRICT_EXEC"
echo "GLUCOSE_EXEC:    $GLUCOSE_EXEC"
echo "DRAT_EXEC:       $DRAT_EXEC"
echo "----------------------------------"
echo

mkdir -p $OUT_DIRECTORY

for ((i = $BEGIN_ROUNDS; i <= $END_ROUNDS; i++)); do
    OUT_SUBDIRECTORY="${OUT_DIRECTORY}/${i}_rounds"
    mkdir -p $OUT_SUBDIRECTORY

    for ((j = $BEGIN_RESTRICTIONS; j <= $END_RESTRICTIONS; j++)); do
        OUT_SUBSUBDIRECTORY="${OUT_SUBDIRECTORY}/${j}_restrictions"
        mkdir -p $OUT_SUBSUBDIRECTORY

        BASE_NAME="${i}_${j}_"
        GENERATED_CNF="${OUT_SUBSUBDIRECTORY}/${BASE_NAME}_generated.cnf"
        RESTRICTED_CNF="${OUT_SUBSUBDIRECTORY}/${BASE_NAME}_restricted.cnf"
        DRAT_PROOF="${OUT_SUBSUBDIRECTORY}/${BASE_NAME}_proof.drup"
        CORE_PROOF="${OUT_SUBSUBDIRECTORY}/${BASE_NAME}_core.drat"
        CORE_DEPENDENCY="${OUT_SUBSUBDIRECTORY}/${BASE_NAME}_core.dependency"

        if [[ $OPTION == $OPTION_GLUCOSE ]]; then
            # Generate CNF from a randomly generated SHA-1 instance
            echo "Generating CNF from SHA-1 instance with ${i} rounds and ${j} restrictions..."
            $CRYPTO_EXEC -A counter_chain -r $i --random_target --print_target |
            $CRYPTO_EXEC -A counter_chain -r $i > $GENERATED_CNF

            # Flip n random bits in the generated CNF
            $RESTRICT_EXEC "$j" "$GENERATED_CNF" "$RESTRICTED_CNF"

            if [[ $GENERATE_PROOF == "true" ]]; then
                JOB_COMMAND="${GLUCOSE_EXEC} -certified -certified-output=\"${DRAT_PROOF}\" ${RESTRICTED_CNF}"
            else
                JOB_COMMAND="${GLUCOSE_EXEC} ${RESTRICTED_CNF}"
            fi
        elif [[ $OPTION == $OPTION_DRAT ]]; then
            JOB_COMMAND="${DRAT_EXEC} ${RESTRICTED_CNF} ${DRAT_PROOF} -l ${CORE_PROOF}"
        elif [[ $OPTION == $OPTION_DEPENDENCY ]]; then
            JOB_COMMAND="${DRAT_EXEC} ${RESTRICTED_CNF} ${CORE_PROOF} -r ${CORE_DEPENDENCY}"
        elif [[ $OPTION == $OPTION_GR ]]; then
            JOB_COMMAND="${GR_EXEC} ${OUT_SUBSUBDIRECTORY}/ ${BASE_NAME}_core.dependency"
        fi

        # Generate job file
        echo "Generating job script"
        JOB_SCRIPT="${OUT_SUBSUBDIRECTORY}/${BASE_NAME}_${OPTION}.sh"
        echo "#!/bin/bash" > $JOB_SCRIPT
        echo "#SBATCH --account=def-${SHARCNET_ACCOUNT_NAME}" >> $JOB_SCRIPT
        echo "#SBATCH --time=${SHARCNET_TIMEOUT}" >> $JOB_SCRIPT
        echo "#SBATCH --mem=${SHARCNET_MEMORY}" >> $JOB_SCRIPT
        echo "#SBATCH --job-name=${BASE_NAME}_${OPTION}" >> $JOB_SCRIPT
        echo "#SBATCH --output=${OUT_SUBSUBDIRECTORY}/${BASE_NAME}_${OPTION}.log" >> $JOB_SCRIPT

        echo "echo \"CPU information:\"" >> $JOB_SCRIPT
        echo "echo \$(lscpu)" >> $JOB_SCRIPT
        echo "echo" >> $JOB_SCRIPT
        echo "echo \"RAM information:\"" >> $JOB_SCRIPT
        echo "echo \$(free -m)" >> $JOB_SCRIPT

        echo "time ${JOB_COMMAND}" >> $JOB_SCRIPT

        # Queue job
        sbatch $JOB_SCRIPT

        # Wait between queuing jobs
        sleep 2
    done
done