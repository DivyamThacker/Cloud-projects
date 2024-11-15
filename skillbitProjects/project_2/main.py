import backuplib, sys
if len(sys.argv) < 2:
    backuplib.welcome()
    backuplib.interactive_backup()
else:    
    backuplib.main()