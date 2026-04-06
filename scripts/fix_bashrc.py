import re, os
p = os.path.expanduser('~/.bashrc')
txt = open(p).read()
# Remove any corrupted AMENT_PREFIX_PATH lines
txt = re.sub(r'\nexport AMENT_PREFIX_PATH=.*robot_vision[^\n]*', '', txt)
txt = txt.rstrip() + '\nexport AMENT_PREFIX_PATH="$HOME/ros2_ws/install/robot_vision:$AMENT_PREFIX_PATH"\n'
open(p, 'w').write(txt)
print('bashrc fixed')
