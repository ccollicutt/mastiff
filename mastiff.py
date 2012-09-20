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
        help="Set what group of servers to build from the config file",
        action="store",
        dest="BREED",
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
    nova = client.Client(OS_USERNAME, OS_PASSWORD, OS_TENANT_NAME, OS_AUTH_URL, service_type="compute")

    # XXX FIXME: Must be a better way to test the connection...
    try:
        nova.servers.list()
    except:
        print >>sys.stderr, "ERROR: Could not connect to OpenStack via nova python client"
        sys.exit(1)

   
    if args.BREED:
        BREED = args.BREED
    else:
       # nothing to do
       sys.exit(0)

    try:
        stream = open(BREED + ".yml", 'r')
    except:
        print >>sys.stderr, "ERROR: Failed to open " + BREED + ".yml"
        sys.exit(1)  

    try:
        breed =  yaml.load(stream)
    except:
        print >>sys.stderr, "ERROR: " + BREED + ".yml is not a valid yaml file"
        sys.exit(1) 

    if args.SHELL:
        #ipython_shell(nova)
        ipshell=InteractiveShellEmbed()
        ipshell()
        print "Exiting IPython shell..."
        sys.exit(0)

    instances = breed[str(BREED)]
    servers = []

    for i, k in instances.iteritems():
        for item in k:
            if 'instances' in item:
                num_instances = item['instances']
            elif 'image' in item:
                image = item['image']
            elif 'playbook' in item:
                playbook = item['playbook']
            elif 'flavor' in item:
                flavor = item['flavor']
            else:
                flavor = "1"

        # Don't forget flavor XXX
        if num_instances is not None and image is not None:
            for j in range(int(num_instances)):
                server = nova.servers.create(flavor=flavor,image=image,name=str(BREED) + ' ' + str(i) + ' ' + str(j))
                if server:
                    servers.append(server)
        else:
            print "no num_instances and image"

    for server in servers:
        print server.id

    sys.exit(0)
    
if __name__ == '__main__':
    main(sys.argv)
