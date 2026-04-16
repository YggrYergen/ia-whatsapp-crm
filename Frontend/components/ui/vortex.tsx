"use client";
import { cn } from "@/lib/utils";
import React, { useEffect, useRef, useCallback } from "react";
import { createNoise3D } from "simplex-noise";
import { motion } from "motion/react";

interface VortexProps {
  children?: React.ReactNode;
  className?: string;
  containerClassName?: string;
  particleCount?: number;
  rangeY?: number;
  baseHue?: number;
  baseSpeed?: number;
  rangeSpeed?: number;
  baseRadius?: number;
  rangeRadius?: number;
  backgroundColor?: string;
}

export const Vortex = (props: VortexProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animationFrameId = useRef<number | undefined>(undefined);
  const isVisible = useRef(true);
  const mousePos = useRef<{ x: number; y: number } | null>(null);
  const isTouchDevice = useRef(false);
  const frameCount = useRef(0);
  const particleCount = props.particleCount || 700;
  const particlePropCount = 9;
  const particlePropsLength = particleCount * particlePropCount;
  // Dark matter particles: last 8% of the array
  const darkMatterStart = Math.floor(particleCount * 0.92) * particlePropCount;
  const baseTTL = 50;
  const rangeTTL = 150;
  const baseSpeed = props.baseSpeed || 0.0;
  const rangeSpeed = props.rangeSpeed || 1.5;
  const baseRadius = props.baseRadius || 1;
  const rangeRadius = props.rangeRadius || 2;
  const baseHue = props.baseHue || 220;
  const rangeHue = 100;

  // === DEPTH TUNING: Lower noise frequency = bigger coherent flow structures ===
  // Was 0.00125 — now 0.0009 for wider, more "layered" filaments
  const noiseSteps = 2.5;
  const xOff = 0.0009;
  const yOff = 0.0009;
  const zOff = 0.00035; // Slower temporal evolution = more stable field topology

  const backgroundColor = props.backgroundColor || "#000000";
  let tick = 0;
  const noise3D = createNoise3D();
  // Secondary noise for field-layer modulation
  const noise3D_B = createNoise3D();
  let particleProps = new Float32Array(particlePropsLength);
  let center: [number, number] = [0, 0];

  const TAU: number = 2 * Math.PI;
  const rand = (n: number): number => n * Math.random();
  const fadeInOut = (t: number, m: number): number => {
    let hm = 0.5 * m;
    return Math.abs(((t + hm) % m) - hm) / hm;
  };
  const lerp = (n1: number, n2: number, speed: number): number =>
    (1 - speed) * n1 + speed * n2;

  // === SECONDARY ATTRACTORS: invisible "magnetic objects" ===
  // These orbit slowly, creating layered field convergence zones
  const getSecondaryAttractors = (t: number, w: number, h: number) => {
    return [
      {
        x: w * 0.5 + Math.sin(t * 0.0003) * w * 0.22,
        y: h * 0.5 + Math.cos(t * 0.00025) * h * 0.18,
        strength: 18,
        radius: w * 0.18,
      },
      {
        x: w * 0.5 + Math.cos(t * 0.00022) * w * 0.28,
        y: h * 0.5 + Math.sin(t * 0.00035) * h * 0.22,
        strength: 14,
        radius: w * 0.15,
      },
      {
        x: w * 0.5 + Math.sin(t * 0.00018 + 2.1) * w * 0.16,
        y: h * 0.5 + Math.cos(t * 0.0004 + 1.4) * h * 0.14,
        strength: 10,
        radius: w * 0.12,
      },
    ];
  };

  const setup = () => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (canvas && container) {
      const ctx = canvas.getContext("2d");
      if (ctx) {
        resize(canvas);
        initParticles();
        draw(canvas, ctx);
      }
    }
  };

  const initParticles = () => {
    tick = 0;
    particleProps = new Float32Array(particlePropsLength);
    for (let i = 0; i < particlePropsLength; i += particlePropCount) {
      initParticle(i);
    }
  };

  const initParticle = (i: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const isDarkMatter = i >= darkMatterStart;

    const x = rand(canvas.width);
    const y = rand(canvas.height);
    const vx = 0;
    const vy = 0;
    const life = 0;
    const ttl = baseTTL + rand(rangeTTL);
    const speed = baseSpeed + rand(rangeSpeed);
    // Dark matter: single pixel white dots. Normal: standard radius.
    const radius = isDarkMatter ? 0.5 : baseRadius + rand(rangeRadius);
    // Dark matter: hue=0 signals the renderer to use white/black instead of HSL
    const hue = isDarkMatter ? -1 : baseHue + rand(rangeHue);

    particleProps.set([x, y, vx, vy, life, ttl, speed, radius, hue], i);
  };

  const draw = (canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D) => {
    if (!isVisible.current) {
      animationFrameId.current = undefined;
      return;
    }

    tick++;
    frameCount.current++;

    // Update center — cursor follow or autonomous drift
    const baseX = 0.5 * canvas.width;
    const baseY = 0.5 * canvas.height;

    if (mousePos.current && !isTouchDevice.current) {
      center[0] = lerp(center[0], mousePos.current.x, 0.03);
      center[1] = lerp(center[1], mousePos.current.y, 0.03);
    } else {
      const driftT = tick * 0.0008;
      const driftX = Math.sin(driftT * 1.3) * canvas.width * 0.06;
      const driftY = Math.cos(driftT * 0.9) * canvas.height * 0.04;
      center[0] = lerp(center[0], baseX + driftX, 0.02);
      center[1] = lerp(center[1], baseY + driftY, 0.02);
    }

    // Physics every frame
    updateParticles(canvas);

    // Render every 2nd frame (~30fps visual)
    if (frameCount.current % 2 === 0) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = backgroundColor;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      renderParticles(ctx);
      renderGlow(canvas, ctx);
      renderToScreen(canvas, ctx);
    }

    animationFrameId.current = window.requestAnimationFrame(() =>
      draw(canvas, ctx),
    );
  };

  const resumeAnimation = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (canvas && ctx && !animationFrameId.current) {
      draw(canvas, ctx);
    }
  }, []);

  const updateParticles = (canvas: HTMLCanvasElement) => {
    for (let i = 0; i < particlePropsLength; i += particlePropCount) {
      updateParticlePhysics(i, canvas);
    }
  };

  const renderParticles = (ctx: CanvasRenderingContext2D) => {
    for (let i = 0; i < particlePropsLength; i += particlePropCount) {
      drawParticle(i, ctx);
    }
  };

  const updateParticlePhysics = (i: number, canvas: HTMLCanvasElement) => {
    const i2 = 1 + i,
      i3 = 2 + i,
      i4 = 3 + i,
      i5 = 4 + i,
      i6 = 5 + i,
      i7 = 6 + i;

    const x = particleProps[i];
    const y = particleProps[i2];
    let life = particleProps[i5];
    const ttl = particleProps[i6];
    const speed = particleProps[i7];

    // === PRIMARY ATTRACTOR (black hole at center) ===
    const dx = x - center[0];
    const dy = y - center[1];
    const dist = Math.sqrt(dx * dx + dy * dy);
    const eventHorizon = 8;
    const gravityRadius = canvas.width * 0.28;

    // === LAYERED FIELD: dual-frequency noise for onion-layer topology ===
    // Primary noise: large-scale flow direction
    const n1 = noise3D(x * xOff, y * yOff, tick * zOff) * noiseSteps * TAU;
    // Secondary noise: field-layer modulation — different frequency creates interference
    // This produces the visible "layers" / "shells" in the flow
    const n2 = noise3D_B(x * xOff * 1.7, y * yOff * 1.7, tick * zOff * 0.8) * TAU;
    // Blend: primary dominates, secondary creates layered perturbation
    const fieldLayerIntensity = Math.abs(Math.sin(n2 * 2.0)); // 0–1 oscillation = layer shells
    const n = n1 + n2 * 0.18; // Subtle secondary influence on direction

    // Noise suppression near center
    const gravityZone = Math.max(0, 1 - dist / gravityRadius);
    const noiseLerp = 0.5 * (1 - gravityZone * 0.76);

    let vx = lerp(particleProps[i3], Math.cos(n), noiseLerp);
    let vy = lerp(particleProps[i4], Math.sin(n), noiseLerp);

    // Primary gravity
    if (dist < gravityRadius && dist > eventHorizon) {
      const nx = dx / dist;
      const ny = dy / dist;
      const lifeRatio = life / ttl;
      const gravityFade = lifeRatio < 0.7 ? 1.0 : Math.max(0, 1 - (lifeRatio - 0.7) / 0.25);

      const gravStrength = Math.min(1.1, 50 / (dist + 25)) * gravityFade;
      vx -= nx * gravStrength;
      vy -= ny * gravStrength * 0.35;

      const orbitalStrength = Math.min(0.9, 36 / (dist + 30)) * gravityFade;
      vx += -ny * orbitalStrength;
      vy += nx * orbitalStrength * 0.35;
    }

    // === SECONDARY ATTRACTORS: invisible magnetic objects ===
    const attractors = getSecondaryAttractors(tick, canvas.width, canvas.height);
    for (const att of attractors) {
      const adx = x - att.x;
      const ady = y - att.y;
      const adist = Math.sqrt(adx * adx + ady * ady);
      if (adist < att.radius && adist > 3) {
        const anx = adx / adist;
        const any_ = ady / adist;
        const azone = Math.max(0, 1 - adist / att.radius);

        // Gentle orbital pull — creates visible concentric flow shells
        const orbForce = (att.strength / (adist + 40)) * azone;
        vx += -any_ * orbForce * 0.6;
        vy += anx * orbForce * 0.6;
        // Weak inward pull — just enough to bend particle paths
        vx -= anx * orbForce * 0.15;
        vy -= any_ * orbForce * 0.15;
      }
    }

    // Event horizon
    if (dist <= eventHorizon) {
      initParticle(i);
      return;
    }

    const x2 = x + vx * speed;
    const y2 = y + vy * speed;
    life++;

    particleProps[i] = x2;
    particleProps[i2] = y2;
    particleProps[i3] = vx;
    particleProps[i4] = vy;
    particleProps[i5] = life;

    if (checkBounds(x, y, canvas) || life > ttl) {
      initParticle(i);
    }
  };

  const drawParticle = (i: number, ctx: CanvasRenderingContext2D) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const x = particleProps[i];
    const y = particleProps[i + 1];
    const vx = particleProps[i + 2];
    const vy = particleProps[i + 3];
    const life = particleProps[i + 4];
    const ttl = particleProps[i + 5];
    const radius = particleProps[i + 7];
    const hue = particleProps[i + 8];
    const isDarkMatter = hue < 0;

    // Distance from primary center
    const dx = x - center[0];
    const dy = y - center[1];
    const dist = Math.sqrt(dx * dx + dy * dy);
    const maxDist = canvas.width * 0.31;
    const proximity = Math.max(0, 1 - dist / maxDist);

    const baseAlpha = fadeInOut(life, ttl);

    // === DARK MATTER RENDERING ===
    if (isDarkMatter) {
      // Wide gravity influence zone
      const gravInfluence = Math.max(0, 1 - dist / (canvas.width * 0.35));
      // Size: 0.5px dust → up to 1.5px (3x) near accretion disc
      const dmSize = 0.5 + gravInfluence * gravInfluence * 1.0;
      // Color: white → absolute black as gravity takes hold
      const dmLightness = 90 * (1 - gravInfluence * gravInfluence);
      // Alpha: bright enough to see as dust specks
      const dmAlpha = baseAlpha * 0.9;

      ctx.save();
      ctx.fillStyle = `hsla(0,0%,${dmLightness}%,${Math.min(dmAlpha, 1)})`;
      ctx.beginPath();
      ctx.arc(x, y, dmSize, 0, TAU);
      ctx.fill();
      ctx.restore();
      return;
    }

    // === NORMAL PARTICLE RENDERING ===
    // Field convergence glow
    let fieldBoost = 0;
    const attractors = getSecondaryAttractors(tick, canvas.width, canvas.height);
    for (const att of attractors) {
      const adx = x - att.x;
      const ady = y - att.y;
      const adist = Math.sqrt(adx * adx + ady * ady);
      const aProx = Math.max(0, 1 - adist / (att.radius * 0.7));
      fieldBoost = Math.max(fieldBoost, aProx * 0.4);
    }

    // Velocity-based depth
    const vel = Math.sqrt(vx * vx + vy * vy);
    const velBoost = Math.min(vel * 0.15, 0.3);

    const size = radius * (1 + proximity * 1.25 + fieldBoost * 0.8);
    const brightness = 55 + proximity * 40 + fieldBoost * 25 + velBoost * 15;
    const saturation = 100 - proximity * 45 - fieldBoost * 20;
    const alpha = baseAlpha * (0.75 + proximity * 0.25 + fieldBoost * 0.2);

    ctx.save();
    ctx.fillStyle = `hsla(${hue},${saturation}%,${Math.min(brightness, 95)}%,${Math.min(alpha, 1)})`;
    ctx.beginPath();
    ctx.arc(x, y, Math.max(0.5, size), 0, TAU);
    ctx.fill();
    ctx.restore();
  };

  const checkBounds = (x: number, y: number, canvas: HTMLCanvasElement) => {
    return x > canvas.width || x < 0 || y > canvas.height || y < 0;
  };

  const resize = (canvas: HTMLCanvasElement) => {
    const { innerWidth, innerHeight } = window;
    canvas.width = innerWidth;
    canvas.height = innerHeight;
    center[0] = 0.5 * canvas.width;
    center[1] = 0.5 * canvas.height;
  };

  const renderGlow = (
    canvas: HTMLCanvasElement,
    ctx: CanvasRenderingContext2D,
  ) => {
    ctx.save();
    ctx.filter = "blur(5px) brightness(130%)";
    ctx.globalCompositeOperation = "lighter";
    ctx.drawImage(canvas, 0, 0);
    ctx.restore();
  };

  const renderToScreen = (
    canvas: HTMLCanvasElement,
    ctx: CanvasRenderingContext2D,
  ) => {
    ctx.save();
    ctx.globalCompositeOperation = "source-over";
    ctx.drawImage(canvas, 0, 0);
    ctx.restore();
  };

  const handleResize = () => {
    const canvas = canvasRef.current;
    if (canvas) {
      resize(canvas);
    }
  };

  useEffect(() => {
    isTouchDevice.current = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

    setup();
    window.addEventListener("resize", handleResize);

    const handleMouseMove = (e: MouseEvent) => {
      mousePos.current = { x: e.clientX, y: e.clientY };
    };
    const handleMouseLeave = () => {
      mousePos.current = null;
    };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseleave", handleMouseLeave);

    const observer = new IntersectionObserver(
      ([entry]) => {
        isVisible.current = entry.isIntersecting;
        if (entry.isIntersecting) {
          resumeAnimation();
        }
      },
      { threshold: 0 }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseleave", handleMouseLeave);
      observer.disconnect();
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, []);

  return (
    <div className={cn("relative h-full w-full", props.containerClassName)}>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.5 }}
        ref={containerRef}
        className="absolute inset-0 z-0 flex h-full w-full items-center justify-center bg-transparent"
      >
        <canvas ref={canvasRef}></canvas>
      </motion.div>

      <div className={cn("relative z-10", props.className)}>
        {props.children}
      </div>
    </div>
  );
};
