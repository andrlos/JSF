# Why?
This runner has been written as part of integration the testsuite into Adoptium framework of installer tests.

# How?
It is as easy as running the runner.sh script with or without a few exported variables on a rawhide fedora.

The **INPUT** variable is used as a way of telling the testsuite where can he find the rpms he is supposed to test. Please note, that 
the testsuite is intended to run only a set of rpms of one vendor for one OS and with the same version.. you can test multiple archs at once though. 
In case the INPUT variable is not set, the test will expect the rpms to be in rpms folder in **IT'S** home directory. 

E.g. ```~/JSF/rpms```

The **OUTPUT** variable is used to tell the testsuite where should it store the testresults of the run. Those are going to be .jtr.xml files. 
In case this variable is not set, the framework will leave the test results in their default directory:

```~/JSF/jtregLogs```

So how to run it?
Just export the INPUT and OUTPUT variables if you wish to use them and then run 
```sh JSF/generic_runner/runner.sh```

***Please note*** that the test needs approximately 2-20 hours to run completely, based on 
the number of packages you want to test and the execution of the script requires ***root privileges*** for system setup.

