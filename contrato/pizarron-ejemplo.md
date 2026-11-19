## Ejemplo 5.11 · Foster de una admitancia

## Paso 1 · ¿Es LC? ✔

<!-- lamina polos --polos '0 ±2j' --ceros '±j ±3j' --valores -->
![[ejemplo-1.svg]]

Ceros en $\omega=1$ y $\omega=3$, polos en $0$, $2$ e $\infty$: se intercalan.

## Paso 2 · Residuos

$\displaystyle k_0=\lim_{s\to0}s\,F(s)=\tfrac92$ ✔

$\displaystyle 2k_1=\lim_{s^2\to-4}\frac{(s^2+4)\,F(s)}{s}=-\frac{15}{2}$ ✘

> [!warning] Dónde se rompió
> Un residuo negativo en una LC es imposible. Revisá qué vale $s^2$ **también en el denominador**.

## Paso 3 · La red

| Término | Componente |
|---|---|
| $k_\infty s$ | $C=2$ |
| $k_0/s$ | $L=2/9$ |

<!-- lamina escalera 'C=2 | p:L=2/9 | p:tanque(L1=2/15,C1=15/8)' --empieza p --entrada 'Y(s)' -->
![[ejemplo-2.svg]]
