
echo u should have 
echo - two sets of xml definitions in folders message_definitions/v1.0/  AND ./message_definitions2/v1.0 to run this tool properly they can be symlinks 
echo - have installed the modified ./tools/mavgen.py into path as 'mavgen.py'
echo - have installed ./generator/mavgen.py as part of the packe into the usual location - dont run from sources
echo  pip install . from this folder?

# mkdir tmp ; mkdir tmp2; 
# mkdir message_definitions
# mkdir message_definitions2

# cd message_definitions
# ln -s ~/OpenSolo/modules/mavlink-solo/message_definitions/v1.0/ ./v1.0
# cd ..

# cd message_definitions2
# ln -s ~/OpenSolo/modules/ardupilot-solo/libraries/GCS_MAVLink/message_definitions ./v1.0
# cd ..

# ....

#  mavgen.py -o tmp -o2 tmp2 --lang xmldiff --wire-protocol=2.0 --definitions2=message_definitions2/v1.0/ardupilotmega.xml  message_definitions/v1.0/ardupilotmega.xml 


# ...


# mv message_definitions2 message_definitions2a

# cd message_definitions2
# ln -s ~/opensolo/cubesolo/message_definitions/v1.0/ .
# cd ..

 mavgen.py -o tmp -o2 tmp2 --lang xmldiff --wire-protocol=2.0 --definitions2=message_definitions2/v1.0/ardupilotmega.xml  message_definitions/v1.0/ardupilotmega.xml 
