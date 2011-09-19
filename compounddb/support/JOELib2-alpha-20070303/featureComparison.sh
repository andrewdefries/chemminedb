#!/bin/sh

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

# check JOELIB2
###############################
if test -z "${JOELIB2}" ; then
    echo "ERROR: JOELIB2 not found in your environment."
    echo "Please, set the JOELIB2 variable in your environment to match the"
    echo "location of the JOELib tools you want to use."
    echo "If you are using Cygwin, don't forget to quote your variable, e.g."
    echo "setenv JOELIB2 'd:\workingAt\joelib2'"
    echo "or use setenv JOELIB2 /cygdrive/d/workingAt/joelib2"
    exit
fi

# build class path to libraries
###############################
if test -f ${JAVA_HOME}/lib/tools.jar ; then
    #CLASSPATH=${CLASSPATH}:${JAVA_HOME}/lib/tools.jar:${JAVA_HOME}/lib/classes.jar
    CLASSPATH=${JAVA_HOME}/lib/tools.jar:${JAVA_HOME}/lib/classes.jar:${JOELIB2}/build:.
fi
for l in ${JOELIB2}/lib/*.jar
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
BUILDFILE=${JOELIB2}/ant/build.xml
# convert the unix path to windows
if [ "$OSTYPE" = "cygwin32" ] || [ "$OSTYPE" = "cygwin" ] || [ "$OSTYPE" = "posix" ] ; then
   BUILDFILE=`cygpath --path --windows "$BUILDFILE"`
fi
#echo ${BUILDFILE}

# verbose
#echo ${JAVA_HOME}/bin/java  -classpath ${CLASSPATH} \
#                       joelib2.example.ComparisonExample \
#                      $@


${JAVA_HOME}/bin/java  -classpath ${CLASSPATH} \
                       joelib2.example.ComparisonExample \
                      $@

# restore old CLASSPATH
CLASSPATH=${OLD_CLASSPATH}
                                                                                                                                                                                                                                                                                                           