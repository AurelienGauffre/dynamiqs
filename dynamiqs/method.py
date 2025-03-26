from __future__ import annotations

from typing import Any, ClassVar

import equinox as eqx
from optimistix import AbstractRootFinder

from ._utils import tree_str_inline
from .gradient import Autograd, CheckpointAutograd, ForwardAutograd, Gradient

__all__ = [
    'Dopri5',
    'Dopri8',
    'Euler',
    'EulerMaruyama',
    'Expm',
    'Kvaerno3',
    'Kvaerno5',
    'Rouchon1',
    'Tsit5',
    'Event',
]


_TupleGradient = tuple[type[Gradient], ...]


# === generic methods options
class Method(eqx.Module):
    # should be eqx.AbstractClassVar, but this conflicts with the __future__ imports
    SUPPORTED_GRADIENT: ClassVar[_TupleGradient]

    @classmethod
    def supports_gradient(cls, gradient: Gradient | None) -> bool:
        return isinstance(gradient, cls.SUPPORTED_GRADIENT)

    @classmethod
    def assert_supports_gradient(cls, gradient: Gradient | None) -> None:
        if gradient is not None and not cls.supports_gradient(gradient):
            support_str = ', '.join(f'`{x.__name__}`' for x in cls.SUPPORTED_GRADIENT)
            raise ValueError(
                f'Method `{cls.__name__}` does not support gradient'
                f' `{type(gradient).__name__}` (supported gradient types:'
                f' {support_str}).'
            )

    def __str__(self) -> str:
        return tree_str_inline(self)


# === expm method options
class Expm(Method):
    r"""Explicit matrix exponentiation to compute propagators.

    Explicitly batch-compute the propagators for all time intervals in `tsave`. These
    propagators are then iteratively applied:

    - starting from the initial state for [`dq.sesolve()`][dynamiqs.sesolve] and
      [`dq.mesolve()`][dynamiqs.mesolve], to compute states for all times in `tsave`,
    - starting from the identity matrix for [`dq.sepropagator()`][dynamiqs.sepropagator]
      and [`dq.mepropagator()`][dynamiqs.mepropagator], to compute propagators for all
      times in `tsave`.

    For the Schrödinger equation with constant Hamiltonian $H$, the propagator from
    time $t_0$ to time $t_1$ is an $n\times n$ matrix given by
    $$
        U(t_0, t_1) = \exp(-i (t_1 - t_0) H).
    $$

    For the Lindblad master equation with constant Liouvillian $\mathcal{L}$, the
    problem is vectorized and the propagator from time $t_0$ to time $t_1$ is an
    $n^2\times n^2$ matrix given by
    $$
        \mathcal{U}(t_0, t_1) = \exp((t_1 - t_0)\mathcal{L}).
    $$

    Warning:
        If the Hamiltonian or jump operators are sparse qarrays, they will be silently
        converted to dense qarrays before computing their matrix exponentials.

    Warning:
        This method is not recommended for open systems of large dimension, due to
        the $\mathcal{O}(n^6)$ scaling of computing the Liouvillian exponential.

    Warning:
        This method only supports constant or piecewise constant Hamiltonian and jump
        operators.

    Note-: Supported gradients
        This method supports differentiation with
        [`dq.gradient.Autograd`][dynamiqs.gradient.Autograd] (default).
    """

    SUPPORTED_GRADIENT: ClassVar[_TupleGradient] = (Autograd,)

    # dummy init to have the signature in the documentation
    def __init__(self):
        pass


# === generic ODE/SDE methods options
class _DEMethod(Method):
    pass


class _DEFixedStep(_DEMethod):
    dt: float


class _DEAdaptiveStep(_DEMethod):
    rtol: float = 1e-6
    atol: float = 1e-6
    safety_factor: float = 0.9
    min_factor: float = 0.2
    max_factor: float = 5.0
    max_steps: int = 100_000


# === public methods options
class Euler(_DEFixedStep):
    """Euler method (fixed step size ODE method).

    This method is implemented by the [Diffrax](https://docs.kidger.site/diffrax/)
    library, see [`diffrax.Euler`](https://docs.kidger.site/diffrax/api/solvers/ode_solvers/#diffrax.Euler).

    Warning:
        This method is not recommended for general use.

    Args:
        dt: Fixed time step.

    Note-: Supported gradients
        This method supports differentiation with
        [`dq.gradient.Autograd`][dynamiqs.gradient.Autograd],
        [`dq.gradient.CheckpointAutograd`][dynamiqs.gradient.CheckpointAutograd]
        (default)
        and [`dq.gradient.ForwardAutograd`][dynamiqs.gradient.ForwardAutograd].
    """

    SUPPORTED_GRADIENT: ClassVar[_TupleGradient] = (
        Autograd,
        CheckpointAutograd,
        ForwardAutograd,
    )

    # dummy init to have the signature in the documentation
    def __init__(self, dt: float):
        super().__init__(dt)


class EulerMaruyama(_DEFixedStep):
    r"""Euler-Maruyama method (fixed step size SDE method).

    For a fixed step size $\dt$, it has weak order of convergence $\dt$ and strong order
    of convergence $\sqrt{\dt}$.

    Args:
        dt: Fixed time step.

    Note-: Supported gradients
        This method supports differentiation with
        [`dq.gradient.Autograd`][dynamiqs.gradient.Autograd] (default).
    """

    SUPPORTED_GRADIENT: ClassVar[_TupleGradient] = (Autograd,)

    # dummy init to have the signature in the documentation
    def __init__(self, dt: float):
        super().__init__(dt)


class Rouchon1(_DEFixedStep):
    r"""First-order Rouchon method (fixed step size ODE/SDE method).

    Args:
        dt: Fixed time step.
        normalize: If True, the scheme is trace-preserving to machine precision, which
            is the recommended option because it is much more stable. Otherwise, it is
            only trace-preserving to first order in $\dt$.

    Note-: Supported gradients
        This method supports differentiation with
        [`dq.gradient.Autograd`][dynamiqs.gradient.Autograd],
        [`dq.gradient.CheckpointAutograd`][dynamiqs.gradient.CheckpointAutograd]
        (default)
        and [`dq.gradient.ForwardAutograd`][dynamiqs.gradient.ForwardAutograd].
    """

    SUPPORTED_GRADIENT: ClassVar[_TupleGradient] = (
        Autograd,
        CheckpointAutograd,
        ForwardAutograd,
    )
    normalize: bool

    # dummy init to have the signature in the documentation
    def __init__(self, dt: float, normalize: bool = True):
        super().__init__(dt)
        self.normalize = normalize

    # normalize: The default scheme is trace-preserving at first order only. This
    # parameter sets the normalisation behaviour:
    # - `None`: The scheme is not normalized.
    # - `'sqrt'`: The Kraus map is renormalized with a matrix square root. Ideal
    #   for stiff problems, recommended for time-independent problems.
    # - `cholesky`: The Kraus map is renormalized at each time step using a Cholesky
    #   decomposition. Ideal for stiff problems, recommended for time-dependent
    #   problems.

    # TODO: fix, strings are not valid JAX types
    # normalize: Literal['sqrt', 'cholesky'] | None = None


class Dopri5(_DEAdaptiveStep):
    """Dormand-Prince method of order 5 (adaptive step size ODE method).

    This method is implemented by the [Diffrax](https://docs.kidger.site/diffrax/)
    library, see [`diffrax.Dopri5`](https://docs.kidger.site/diffrax/api/solvers/ode_solvers/#diffrax.Dopri5).

    Args:
        rtol: Relative tolerance.
        atol: Absolute tolerance.
        safety_factor: Safety factor for adaptive step sizing.
        min_factor: Minimum factor for adaptive step sizing.
        max_factor: Maximum factor for adaptive step sizing.
        max_steps: Maximum number of steps.

    Note-: Supported gradients
        This method supports differentiation with
        [`dq.gradient.Autograd`][dynamiqs.gradient.Autograd],
        [`dq.gradient.CheckpointAutograd`][dynamiqs.gradient.CheckpointAutograd]
        (default)
        and [`dq.gradient.ForwardAutograd`][dynamiqs.gradient.ForwardAutograd].
    """

    SUPPORTED_GRADIENT: ClassVar[_TupleGradient] = (
        Autograd,
        CheckpointAutograd,
        ForwardAutograd,
    )

    # dummy init to have the signature in the documentation
    def __init__(
        self,
        rtol: float = 1e-6,
        atol: float = 1e-6,
        safety_factor: float = 0.9,
        min_factor: float = 0.2,
        max_factor: float = 5.0,
        max_steps: int = 100_000,
    ):
        super().__init__(rtol, atol, safety_factor, min_factor, max_factor, max_steps)


class Dopri8(_DEAdaptiveStep):
    """Dormand-Prince method of order 8 (adaptive step size ODE method).

    This method is implemented by the [Diffrax](https://docs.kidger.site/diffrax/)
    library, see [`diffrax.Dopri8`](https://docs.kidger.site/diffrax/api/solvers/ode_solvers/#diffrax.Dopri8).

    Args:
        rtol: Relative tolerance.
        atol: Absolute tolerance.
        safety_factor: Safety factor for adaptive step sizing.
        min_factor: Minimum factor for adaptive step sizing.
        max_factor: Maximum factor for adaptive step sizing.
        max_steps: Maximum number of steps.

    Note-: Supported gradients
        This method supports differentiation with
        [`dq.gradient.Autograd`][dynamiqs.gradient.Autograd],
        [`dq.gradient.CheckpointAutograd`][dynamiqs.gradient.CheckpointAutograd]
        (default)
        and [`dq.gradient.ForwardAutograd`][dynamiqs.gradient.ForwardAutograd].
    """

    SUPPORTED_GRADIENT: ClassVar[_TupleGradient] = (
        Autograd,
        CheckpointAutograd,
        ForwardAutograd,
    )

    # dummy init to have the signature in the documentation
    def __init__(
        self,
        rtol: float = 1e-6,
        atol: float = 1e-6,
        safety_factor: float = 0.9,
        min_factor: float = 0.2,
        max_factor: float = 5.0,
        max_steps: int = 100_000,
    ):
        super().__init__(rtol, atol, safety_factor, min_factor, max_factor, max_steps)


class Tsit5(_DEAdaptiveStep):
    """Tsitouras method of order 5 (adaptive step size ODE method).

    This method is implemented by the [Diffrax](https://docs.kidger.site/diffrax/)
    library, see [`diffrax.Tsit5`](https://docs.kidger.site/diffrax/api/solvers/ode_solvers/#diffrax.Tsit5).

    Args:
        rtol: Relative tolerance.
        atol: Absolute tolerance.
        safety_factor: Safety factor for adaptive step sizing.
        min_factor: Minimum factor for adaptive step sizing.
        max_factor: Maximum factor for adaptive step sizing.
        max_steps: Maximum number of steps.

    Note-: Supported gradients
        This method supports differentiation with
        [`dq.gradient.Autograd`][dynamiqs.gradient.Autograd],
        [`dq.gradient.CheckpointAutograd`][dynamiqs.gradient.CheckpointAutograd]
        (default)
        and [`dq.gradient.ForwardAutograd`][dynamiqs.gradient.ForwardAutograd].
    """

    SUPPORTED_GRADIENT: ClassVar[_TupleGradient] = (
        Autograd,
        CheckpointAutograd,
        ForwardAutograd,
    )

    # dummy init to have the signature in the documentation
    def __init__(
        self,
        rtol: float = 1e-6,
        atol: float = 1e-6,
        safety_factor: float = 0.9,
        min_factor: float = 0.2,
        max_factor: float = 5.0,
        max_steps: int = 100_000,
    ):
        super().__init__(rtol, atol, safety_factor, min_factor, max_factor, max_steps)


class Kvaerno3(_DEAdaptiveStep):
    """Kvaerno's method of order 3 (adaptive step size and implicit ODE method).

    This method is suitable for stiff problems, typically those with Hamiltonians or
    Liouvillians that have eigenvalues spanning different orders of magnitudes. This is
    for instance the case with problems involving high-order polynomials of the bosonic
    annihilation and creation operators, in large dimensions.

    This method is implemented by the [Diffrax](https://docs.kidger.site/diffrax/)
    library, see [`diffrax.Kvaerno3`](https://docs.kidger.site/diffrax/api/solvers/ode_solvers/#diffrax.Kvaerno3).

    Warning:
        If you find that your simulation is slow or that the progress bar gets stuck,
        consider switching to double-precision with
        [`dq.set_precision('double')`][dynamiqs.set_precision]. See more details in
        [The sharp bits 🔪](../../documentation/getting_started/sharp-bits.md) tutorial.

    Args:
        rtol: Relative tolerance.
        atol: Absolute tolerance.
        safety_factor: Safety factor for adaptive step sizing.
        min_factor: Minimum factor for adaptive step sizing.
        max_factor: Maximum factor for adaptive step sizing.
        max_steps: Maximum number of steps.

    Note-: Supported gradients
        This method supports differentiation with
        [`dq.gradient.Autograd`][dynamiqs.gradient.Autograd],
        [`dq.gradient.CheckpointAutograd`][dynamiqs.gradient.CheckpointAutograd]
        (default)
        and [`dq.gradient.ForwardAutograd`][dynamiqs.gradient.ForwardAutograd].
    """

    SUPPORTED_GRADIENT: ClassVar[_TupleGradient] = (
        Autograd,
        CheckpointAutograd,
        ForwardAutograd,
    )

    # dummy init to have the signature in the documentation
    def __init__(
        self,
        rtol: float = 1e-6,
        atol: float = 1e-6,
        safety_factor: float = 0.9,
        min_factor: float = 0.2,
        max_factor: float = 5.0,
        max_steps: int = 100_000,
    ):
        super().__init__(rtol, atol, safety_factor, min_factor, max_factor, max_steps)


class Kvaerno5(_DEAdaptiveStep):
    """Kvaerno's method of order 5 (adaptive step size and implicit ODE method).

    This method is suitable for stiff problems, typically those with Hamiltonians or
    Liouvillians that have eigenvalues spanning different orders of magnitudes. This is
    for instance the case with problems involving high-order polynomials of the bosonic
    annihilation and creation operators, in large dimensions.

    This method is implemented by the [Diffrax](https://docs.kidger.site/diffrax/)
    library, see [`diffrax.Kvaerno5`](https://docs.kidger.site/diffrax/api/solvers/ode_solvers/#diffrax.Kvaerno5).

    Warning:
        If you find that your simulation is slow or that the progress bar gets stuck,
        consider switching to double-precision with
        [`dq.set_precision('double')`][dynamiqs.set_precision]. See more details in
        [The sharp bits 🔪](../../documentation/getting_started/sharp-bits.md) tutorial.

    Args:
        rtol: Relative tolerance.
        atol: Absolute tolerance.
        safety_factor: Safety factor for adaptive step sizing.
        min_factor: Minimum factor for adaptive step sizing.
        max_factor: Maximum factor for adaptive step sizing.
        max_steps: Maximum number of steps.

    Note-: Supported gradients
        This method supports differentiation with
        [`dq.gradient.Autograd`][dynamiqs.gradient.Autograd],
        [`dq.gradient.CheckpointAutograd`][dynamiqs.gradient.CheckpointAutograd]
        (default)
        and [`dq.gradient.ForwardAutograd`][dynamiqs.gradient.ForwardAutograd].
    """

    SUPPORTED_GRADIENT: ClassVar[_TupleGradient] = (
        Autograd,
        CheckpointAutograd,
        ForwardAutograd,
    )

    # dummy init to have the signature in the documentation
    def __init__(
        self,
        rtol: float = 1e-6,
        atol: float = 1e-6,
        safety_factor: float = 0.9,
        min_factor: float = 0.2,
        max_factor: float = 5.0,
        max_steps: int = 100_000,
    ):
        super().__init__(rtol, atol, safety_factor, min_factor, max_factor, max_steps)


class Event(_DEMethod):
    """Event method for the jump SSE and SME.

    This method uses the [Diffrax](https://docs.kidger.site/diffrax/) library event
    handling to interrupt the no-click integration at the next sampled click time,
    apply the corresponding measurement backaction to the state, and continue the
    no-click integration until the subsequent sampled click time.

    Note: Click times precision
        By default, the click time precision is determined by the integration step size.
        The exact click time can be refined to a chosen precision by specifying the
        `root_finder` argument, see for example the
        [optimistix library Newton root finder](https://docs.kidger.site/optimistix/api/root_find/#optimistix.Newton).

    Args:
        noclick_method: Method for the no-click evolution. Defaults to
            [`dq.method.Tsit5`][dynamiqs.method.Tsit5] (supported:
            [`Tsit5`][dynamiqs.method.Tsit5], [`Dopri5`][dynamiqs.method.Dopri5],
            [`Dopri8`][dynamiqs.method.Dopri8],
            [`Kvaerno3`][dynamiqs.method.Kvaerno3],
            [`Kvaerno5`][dynamiqs.method.Kvaerno5],
            [`Euler`][dynamiqs.method.Euler]).
        root_finder: Root finder to refine the click times, defaults to `None`
            (precision determined by the integration step size).
        smart_sampling: If `True`, the no-click trajectory is sampled only once, and
            `result.states` contains only trajectories with one or more clicks. Use
            `result.noclick_states` to access the no-click trajectory, and
            `result.noclick_prob` for its associated probability.

    Note-: Supported gradients
        This method supports differentiation with
        [`dq.gradient.Autograd`][dynamiqs.gradient.Autograd],
        [`dq.gradient.CheckpointAutograd`][dynamiqs.gradient.CheckpointAutograd]
        (default)
        and [`dq.gradient.ForwardAutograd`][dynamiqs.gradient.ForwardAutograd].
    """

    noclick_method: Method = Tsit5()
    root_finder: AbstractRootFinder | None = None
    smart_sampling: bool = False

    SUPPORTED_GRADIENT: ClassVar[_TupleGradient] = (
        Autograd,
        CheckpointAutograd,
        ForwardAutograd,
    )

    # dummy init to have the signature in the documentation
    def __init__(
        self,
        noclick_method: Method = Tsit5(),  # noqa: B008
        root_finder: AbstractRootFinder | None = None,
        smart_sampling: bool = False,
    ):
        self.noclick_method = noclick_method
        self.root_finder = root_finder
        self.smart_sampling = smart_sampling

    # inherit attributes from the noclick_method
    def __getattr__(self, attr: str) -> Any:
        return getattr(self.noclick_method, attr)
