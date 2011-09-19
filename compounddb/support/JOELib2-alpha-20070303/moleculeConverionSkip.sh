#!/bin/sh

#if [ $# -ne 2 ]
#then
#  echo "Usage: your usage"
#  exit 1
#fi

#--------------------------------------------
# No need to edit anything past here
#--------------------------------------------
OLD_CLASSPATH=${CLASSPATH}

# check JAVA_HOME
###############################
if test -z "${JAVA_HOME}" ; then
    echo "ERROR: JAVA_HOME not found in your environment."
    echo "Please, set the JAVA_HOME variable in your environment to match the"
    echo "location of the Java Virtual Machine you want to use."
    echo "If you are using Cygwin, don't forget to quote your variable, e.g."
    echo "setenv JAVA_HOME 'd:\Programme\j2sdk1.4.1'"
    echo "or use setenv JAVA_HOME /cygdrive/c/Programme/j2sdk1.4.1"
    exit
fi

# check JCOMPCHEM
###############################
if test -z "${JCOMPCHEM}" ; then
    echo "ERROR: JCOMPCHEM not found in your environment."
    echo "Please, set the JCOMPCHEM variable in your environment to match the"
    echo "location of the JCompChem tools you want to use."
    echo "If you are using Cygwin, don't forget to quote your variable, e.g."
    echo "setenv JCOMPCHEM 'd:\workingAt\JCompChem'"
    echo "or use setenv JCOMPCHEM /cygdrive/d/workingAt/JCompChem"
    exit
fi

# build class path to libraries
###############################
if test -f ${JAVA_HOME}/lib/tools.jar ; then
    #CLASSPATH=${CLASSPATH}:${JAVA_HOME}/lib/tools.jar:${JAVA_HOME}/lib/classes.jar
    CLASSPATH=${JAVA_HOME}/lib/tools.jar:${JAVA_HOME}/lib/classes.jar:${JCOMPCHEM}/build:.
fi
for l in ${JCOMPCHEM}/lib/*.jar
do
#echo "Adding $l to CLASSPATH."
CLASSPATH=${CLASSPATH}:$l
done
# convert the unix path to windows
if [ "$OSTYPE" = "cygwin32" ] || [ "$OSTYPE" = "cygwin" ] || [ "$OSTYPE" = "posix" ] ; then
   CLASSPATH=`cygpath --path --windows "$CLASSPATH"`
fi
# verbose classpath
#echo "--$CLASSPATH--"

# build path to ANT build file
###############################
BUILDFILE=${JCOMPCHEM}/ant/build.xml
# convert the unix path to windows
if [ "$OSTYPE" = "cygwin32" ] || [ "$OSTYPE" = "cygwin" ] || [ "$OSTYPE" = "posix" ] ; then
   BUILDFILE=`cygpath --path --windows "$BUILDFILE"`
fi
#echo ${BUILDFILE}

#echo ${JAVA_HOME}/bin/java  -classpath ${CLASSPATH} \
#                       joelib2.example.ConvertSkipExample \
#                      $@


${JAVA_HOME}/bin/java  -classpath ${CLASSPATH} \
                       joelib2.example.ConvertSkipExample \
                      $@

# restore old CLASSPATH
CLASSPATH=${OLD_CLASSPATH}
                                                                                                                                                                                                                                                                                                           