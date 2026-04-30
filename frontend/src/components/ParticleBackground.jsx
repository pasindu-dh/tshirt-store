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
        left: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none", // ✅ allows clicking through particles
      }}
      options={{
        fullScreen: {
          enable: true,
          zIndex: -1,
        },

        background: {
          color: {
            value: "transparent",
          },
        },

        fpsLimit: 60,

        particles: {
          number: {
            value: 50, // balanced amount
            density: {
              enable: true,
              area: 800,
            },
          },

          color: {
            value: "#22d3ee", // cyan theme
          },

          shape: {
            type: "circle",
          },

          opacity: {
            value: { min: 0.2, max: 0.4 }, // soft variation
          },

          size: {
            value: { min: 1, max: 3 },
          },

          links: {
            enable: true,
            distance: 150,
            color: "#22d3ee",
            opacity: 0.2,
            width: 1,
          },

          move: {
            enable: true,
            speed: 1, // smooth slow movement
            outModes: {
              default: "out",
            },
          },
        },

        interactivity: {
          events: {
            onHover: {
              enable: true,
              mode: "grab",
            },
            onClick: {
              enable: false,
            },
          },

          modes: {
            grab: {
              distance: 120,
              links: {
                opacity: 0.4,
              },
            },
          },
        },

        detectRetina: true,
      }}
    />
  );
}

export default ParticleBackground;