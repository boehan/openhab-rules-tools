"""
Copyright June 24, 2020 Richard Koshak

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from Queue import Queue
from core.actions import ScriptExecution
from org.joda.time import DateTime
from community.time_utils import to_datetime

class Gatekeeper(object):
    """Keeps a queue of commands and enforce a minimum time after a command
    before a new one can be issued. Adding a command to the gatekeeper is
    non-blocking.
    Examples:
        gk = gatekeeper(logger)
        # Execute a command and wait 1 second before allowing the next.
        gk.add_command(1000, lambda: events.sendCommand("MyItem", "ON"))
        # Adds a command that will wait unti the previous command has
        # expired and then will block for 1 1/2 second.
        gk.add_command(1500, lambda: events.sendCommand("MyTTSItem", "Hello world")
    Functions:
        - add_command: Called to add a command to the queue to be executed when
        the time is right.
    """

    def __init__(self, log):
        """Initializes the queue and timer that drive the gatekeeper."""
        self.commands = Queue()
        self.timer = None
        self.log = log

    def __proc_command(self):
        """
        Called when it is time to execute another command. This function
        simply returns if the queue is empty. Otherwise it pops the next
        command, executes that command, and then sets a Timer to go off the
        given number of milliseconds and call __proc_command again to process
        the next command.
        """
        # No more commands
        if self.commands.empty():
            self.timer = None
            return

        # Pop the next command and run it
        cmd = self.commands.get()
        funct = cmd[1]
        before = DateTime.now().millis
        funct()
        after = DateTime.now().millis

        # Calculate how long to sleep
        delta = after - before
        pause = to_datetime(cmd[0])
        trigger_time = to_datetime(cmd[0]).minusMillis(delta)

        # Create/reschedule the Timer
        if not self.timer:
            self.timer = ScriptExecution.createTimer(trigger_time,
                                                     self.__proc_command)
        else:
            self.timer.reschedule(trigger_time)

    def add_command(self, pause, command):
        """
        Adds a new command to the queue. If it has been long enough since the
        last command executed immediately execute this command. If not it waits
        until enough time has passed. The time required to execute command is
        included in the amount of time to wait. For example, if the command
        takes 250 msec and the pause is 1000 msec, the next command will be
        allowed to execute 750 msec after the command returns.
        Args:
            - pause: Time in any format supported by time_utils.to_datetime.
            - command: Lambda or function to call to execute the command.
        """
        self.commands.put((pause, command))
        if self.timer is None or self.timer.hasTerminated():
            self.__proc_command()

    def cancel_all(self):
        """ Call to clear out the enqueued commands without running them. """
        self.log.debug("Clearing out all enqueued commands")
        while not self.commands.empty():
            self.commands.get(False)
