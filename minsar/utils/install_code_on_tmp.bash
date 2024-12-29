##! /bin/bash

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
helptext="                                                                              \n\
  Examples:                                                                             \n\
      install_code_on_tmp.bash                                                          \n\
      install_code_on_tmp.bash smallbaseline_wrapper.job                                \n\
      install_code_on_tmp.bash mintpy                                                   \n\
      install_code_on_tmp.bash miaplpy.job                                               \n\
      install_code_on_tmp.bash miaplpy                                                   \n\
      install_code_on_tmp.bash insarmaps                                                \n\
                                                                                        \n\
  Installs code on /tmp (includes MintPy, MinoPy, insarmaps_ingest depending on options)\n                                                          \n
     "
printf "$helptext"
exit 0;
fi

###########################################
job_name="$1"

module load TACC
if [[ $PLATFORM_NAME == *"stampede3"* ]]; then
    export CDTOOL=/scratch/01255/siliu/collect_distribute
elif [[ $PLATFORM_NAME == *"frontera"* ]]; then
    export CDTOOL=/scratch1/01255/siliu/collect_distribute
fi
module load intel/19.1.1 2> /dev/null
export PATH=${PATH}:${CDTOOL}/bin

#df -h /tmp
echo -e "\ninstall_code_on_tmp.bash: before copy-to-tmp:\n `df -h /tmp`"
rm -rf /tmp/minsar
mkdir -p /tmp/minsar
mkdir -p /tmp/minsar/tools ;
mkdir -p /tmp/minsar/sources ;

code_dir=$(echo $(basename $(dirname $MINSAR_HOME)))
distribute.bash $SCRATCHDIR/${code_dir}_miniconda3.tar
distribute.bash $SCRATCHDIR/${code_dir}_minsar.tar
tar xf /tmp/${code_dir}_miniconda3.tar -C /tmp/minsar/tools
tar xf /tmp/${code_dir}_minsar.tar -C /tmp/minsar
rm /tmp/${code_dir}_miniconda3.tar
rm /tmp/${code_dir}_minsar.tar

#echo -e "install_code_on_tmp.bash: after copy-to-tmp:\n `df -h /tmp`"


echo "#### To set environment: ####"
echo "export PATH=/bin; export MINSAR_HOME=/tmp/minsar; cd \$MINSAR_HOME; source ~/accounts/platforms_defaults.bash; source setup/environment.bash; export PATH=\$ISCE_STACK/topsStack:\$PATH; cd -;"

