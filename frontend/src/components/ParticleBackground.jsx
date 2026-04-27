import { useCallback } from "react";
import Particles from "@tsparticles/react";
import { loadFull } from "tsparticles";

function ParticleBackground() {

  const particlesInit = useCallback(async (engine) => {
    await loadFull(engine);
  }, []);

  return (
    <Particles
      id="tsparticles"
      init={particlesInit}
      style={{
        position: "fixed",
        top: 0,
        left: 0
      }}
      options={{
        fullScreen: {
          enable: true,
          zIndex: -1
        },

        background: {
        color: {
            value: "transparent"
        }
        },

        particles: {
          number: {
            value: 200,
            density: {
              enable: true,
              area: 800
            }
          },

        color: {
        value: "#ffffff"   // 🔥 bright white
        },

          shape: {
            type: "circle"
          },

          opacity: {
            value: 0.9
          },

          size: {
            value: 6,
          },

        links: {
        enable: true,
        distance: 140,
        color: "#ffffff",
        opacity: 0.7,   // 🔥 increase
        width: 1
        },

          move: {
            enable: true,
            speed: 5,
            direction: "none",
            outModes: {
              default: "bounce"
            }
          }
        },

        interactivity: {
          events: {
            onHover: {
              enable: true,
              mode: ["grab", "bubble"]
            },
            onClick: {
              enable: true,
              mode: "push"
            }
          },

          modes: {
            grab: {
              distance: 250,
              links: {
                opacity: 1
              }
            },

            bubble: {
              distance: 250,
              size: 15,
              duration: 0.8
            },

            push: {
              quantity: 6
            }
          }
        }
      }}
    />
  );
}

export default ParticleBackground;