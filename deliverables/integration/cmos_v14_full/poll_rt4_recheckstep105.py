"""Resume only run104's bounded collector over the verified existing SSH route.

Retains the original shared OS lock, input gates, two stable terminal checks,
and full output validation. Never starts or cancels a simulation.
"""
import poll_rt4_recheckstep104 as previous
from rt4_recheckstep_transport105 import SSH, verify_identity


def main():
    verify_identity()
    previous.r.SSH = SSH
    previous.main()


if __name__ == '__main__':
    main()
