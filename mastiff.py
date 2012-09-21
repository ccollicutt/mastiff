#!/usr/bin/python

import re
import sys
import os, os.path
import ConfigParser

try:
    from novaclient.v1_1 import client
except ImportError:
    print >>sys.stderr, 'ERROR: requires python novaclient'
    sys.exit(1)

try:
    import argparse
except ImportError:
    print >>sys.stderr, 'ERROR: requires argparse'
    sys.exit(1)

try:
    from IPython.frontend.terminal.embed import InteractiveShellEmbed
    ipshell = InteractiveShellEmbed.instance()
except ImportError:
    print >>sys.stderr, 'ERROR: requires IPython'
    sys.exit(1)

try:
    import ansible.runner
except ImportError:
    print >>sys.stderr, 'ERROR: requires ansible'
    sys.exit(1)

try: 
    import yaml
except ImportError:
    print >>sys.stderr, "ERROR: requires pyaml"
    sys.exit(1)


CONFIG_FILE = "./mastiff.conf"

#
# MAIN
# 
def main(args):
    
    # Much of the argparse/configparser parts taken from 
    # http://blog.vwelch.com/2011/04/combining-configparser-and-argparse.html

    conf_parser = argparse.ArgumentParser(
        # Turn off help, so we print all options in response to -h
        add_help=False
    )

    conf_parser.add_argument(
        "-c", "--config-file", 
        dest="configfile", 
        help="Use a different config file than %s" % CONFIG_FILE
    )

    args, remaining_argv = conf_parser.parse_known_args()

    if args.configfile:
        configfile = args.configfile
    else:
        configfile = CONFIG_FILE

    # Make sure the configfile is a file
    if not os.path.isfile(configfile):
        print >>sys.stderr, 'ERROR: %s is not a file' % configfile
        sys.exit(1)

    config = ConfigParser.SafeConfigParser()
    try:
        config.read([configfile])
    except:
        print >>sys.stderr, 'ERROR: There is an error in the config file'
        sys.exit(1)

    defaults = dict(config.items("default"))

    parser = argparse.ArgumentParser(
        # Inherit options from config_parser
        parents=[conf_parser],
        # print script description with -h/--help
        description=__doc__,
        # Don't mess with format of description
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.set_defaults(**defaults)

    #---------------------------------------------------------------------------
    # Add more arguments here!
    #
    # Eg.
    #
    #   parser.add_argument(
    #    "-s", "--somearg", 
    #    dest="somearg", 
    #    help="Replace this with a real argument!"
    #)

    parser.add_argument(
        "--shell", 
        help="Start an interactive IPython shell",
        action="store_true",
        dest="SHELL",
        default=False
    )

    parser.add_argument(
        "--breed", 
        help="Set the breed to load from the breed file",
        action="store",
        dest="BREED",
    )

    parser.add_argument(
        "--breed-file", 
        help="The file that contains all of the breeds",
        action="store",
        dest="BREEDFILE",
    )


    #
    # Done with arguments
    #---------------------------------------------------------------------------

    # Capture args
    args = parser.parse_args(remaining_argv)

    # Makes args into a dictionary to feed to searchList
    d = args.__dict__

    try:
        OS_USERNAME = os.environ['OS_USERNAME']
        OS_TENANT_NAME = os.environ['OS_TENANT_NAME']
        OS_PASSWORD = os.environ['OS_PASSWORD']
        OS_AUTH_URL = os.environ['OS_AUTH_URL']
    except:
        print >>sys.stderr, "ERROR: Openstack environment variables username, tenant name, password, and auth url must be set"
        sys.exit(1)

    # Connect to nova
    nova_compute = client.Client(OS_USERNAME, OS_PASSWORD, OS_TENANT_NAME, OS_AUTH_URL, service_type="compute")
    nova_volume = client.Client(OS_USERNAME, OS_PASSWORD, OS_TENANT_NAME, OS_AUTH_URL, service_type="volume")

    # XXX FIXME: Must be a better way to test the connection...
    try:
        nova_volume.volumes.list()
        nova_compute.servers.list()
    except:
        print >>sys.stderr, "ERROR: Could not connect to OpenStack via nova python client"
        sys.exit(1)

   
    if args.BREED and args.BREEDFILE:
        BREED = args.BREED
        BREEDFILE = args.BREEDFILE
    else:
       # nothing to do
       sys.exit(0)

    try:
        stream = open(BREEDFILE, 'r')
    except:
        print >>sys.stderr, "ERROR: Failed to open " + BREEDFILE
        sys.exit(1)  

    try:
        breed =  yaml.load(stream)
    except:
        print >>sys.stderr, "ERROR: " + BREEDFILE + " is not a valid yaml file"
        sys.exit(1) 

    # If we asked for a shell, open one
    if args.SHELL:
        #ipython_shell(nova)
        ipshell=InteractiveShellEmbed()
        ipshell()
        print "Exiting IPython shell..."
        sys.exit(0)

    # Grab the breed we are looking for from the command line
    # the idea being there could be several breeds in one config file
    # maybe
    instances = breed[str(BREED)]
    servers = []

    # Step through the instance information from the yaml file and boot a bunch of servers
    for i, k in instances.iteritems():
        for item in k:
            # grab each required variable if it's there
            if 'instances' in item:
                num_instances = item['instances']
            elif 'image' in item:
                image = item['image']
            elif 'playbook' in item:
                playbook = item['playbook']
            elif 'flavor' in item:
                flavor = item['flavor']
        
        if flavor is None:
            flavor = 1

        # Don't forget flavor XXX
        if num_instances is not None and image is not None:
            for j in range(int(num_instances)):
                name = str(BREED) + ' ' + str(i) + ' ' + str(j)
                server = nova_compute.servers.create(flavor=flavor,image=image,name=name)
                if server:
                    servers.append(server)

    for server in servers:
        print server.id

    sys.exit(0)
    
if __name__ == '__main__':
    main(sys.argv)
