"""
Independent Component Analysis (ICA) Module.

Implements various ICA algorithms for blind source separation:
- FastICA
- Infomax ICA
- Natural Gradient ICA
"""

import numpy as np
from scipy import linalg
from typing import Optional, Tuple, List, Callable
from dataclasses import dataclass
from enum import Enum


class ICAMethod(Enum):
    """ICA algorithm methods."""
    FASTICA = "fastica"
    INFOMAX = "infomax"
    NATURAL_GRADIENT = "natural_gradient"


class NonlinearityType(Enum):
    """Nonlinearity functions for FastICA."""
    LOGCOSH = "logcosh"
    EXP = "exp"
    CUBE = "cube"
    TANH = "tanh"


@dataclass
class ICAResult:
    """Result of ICA decomposition."""

    sources: np.ndarray  # Separated sources (n_sources, n_samples)
    mixing_matrix: np.ndarray  # Estimated mixing matrix A
    unmixing_matrix: np.ndarray  # Estimated unmixing matrix W
    n_iterations: int  # Number of iterations to converge
    converged: bool  # Whether algorithm converged
    mean: np.ndarray  # Mean of original signals (for reconstruction)


class ICAProcessor:
    """
    Independent Component Analysis processor.

    Implements multiple ICA algorithms for separating mixed signals
    into statistically independent components.
    """

    def __init__(
        self,
        n_components: Optional[int] = None,
        method: ICAMethod = ICAMethod.FASTICA,
        max_iterations: int = 1000,
        tolerance: float = 1e-6,
        random_state: Optional[int] = None,
    ):
        """
        Initialize ICA processor.

        Args:
            n_components: Number of components to extract. None = all.
            method: ICA algorithm to use.
            max_iterations: Maximum iterations for convergence.
            tolerance: Convergence tolerance.
            random_state: Random seed for reproducibility.
        """
        self.n_components = n_components
        self.method = method
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.random_state = random_state

        if random_state is not None:
            np.random.seed(random_state)

    def fit_transform(
        self,
        mixed_signals: np.ndarray,
        nonlinearity: NonlinearityType = NonlinearityType.LOGCOSH,
    ) -> ICAResult:
        """
        Perform ICA on mixed signals.

        Args:
            mixed_signals: Mixed signals array (n_channels, n_samples).
            nonlinearity: Nonlinearity function for FastICA.

        Returns:
            ICAResult with separated sources and matrices.
        """
        # Ensure 2D array
        if mixed_signals.ndim == 1:
            mixed_signals = mixed_signals.reshape(1, -1)

        n_channels, n_samples = mixed_signals.shape
        n_components = self.n_components or n_channels

        # Center the data
        mean = np.mean(mixed_signals, axis=1, keepdims=True)
        centered = mixed_signals - mean

        # Whiten the data
        whitened, whitening_matrix = self._whiten(centered, n_components)

        # Apply ICA algorithm
        if self.method == ICAMethod.FASTICA:
            unmixing, n_iter, converged = self._fastica(
                whitened, n_components, nonlinearity
            )
        elif self.method == ICAMethod.INFOMAX:
            unmixing, n_iter, converged = self._infomax(whitened, n_components)
        elif self.method == ICAMethod.NATURAL_GRADIENT:
            unmixing, n_iter, converged = self._natural_gradient(whitened, n_components)
        else:
            raise ValueError(f"Unknown ICA method: {self.method}")

        # Compute separated sources
        sources = np.dot(unmixing, whitened)

        # Compute full unmixing matrix (including whitening)
        full_unmixing = np.dot(unmixing, whitening_matrix)

        # Estimate mixing matrix (pseudo-inverse of unmixing)
        mixing_matrix = linalg.pinv(full_unmixing)

        return ICAResult(
            sources=sources,
            mixing_matrix=mixing_matrix,
            unmixing_matrix=full_unmixing,
            n_iterations=n_iter,
            converged=converged,
            mean=mean.flatten(),
        )

    def _whiten(
        self,
        data: np.ndarray,
        n_components: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Whiten data using PCA.

        Args:
            data: Centered data (n_channels, n_samples).
            n_components: Number of components to keep.

        Returns:
            Tuple of (whitened_data, whitening_matrix).
        """
        # Compute covariance
        covariance = np.dot(data, data.T) / data.shape[1]

        # Eigendecomposition
        eigenvalues, eigenvectors = linalg.eigh(covariance)

        # Sort by eigenvalues (descending)
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        # Keep top components
        eigenvalues = eigenvalues[:n_components]
        eigenvectors = eigenvectors[:, :n_components]

        # Compute whitening matrix
        # W = D^(-1/2) * V^T where D is diagonal of eigenvalues
        d_inv_sqrt = np.diag(1.0 / np.sqrt(eigenvalues + 1e-10))
        whitening_matrix = np.dot(d_inv_sqrt, eigenvectors.T)

        # Whiten data
        whitened = np.dot(whitening_matrix, data)

        return whitened, whitening_matrix

    def _fastica(
        self,
        whitened: np.ndarray,
        n_components: int,
        nonlinearity: NonlinearityType,
    ) -> Tuple[np.ndarray, int, bool]:
        """
        FastICA algorithm with deflation.

        Args:
            whitened: Whitened data.
            n_components: Number of components.
            nonlinearity: Nonlinearity type.

        Returns:
            Tuple of (unmixing_matrix, iterations, converged).
        """
        n_features, n_samples = whitened.shape

        # Get nonlinearity functions
        g, g_prime = self._get_nonlinearity(nonlinearity)

        # Initialize unmixing matrix
        W = np.random.randn(n_components, n_features)
        W = self._symmetric_orthogonalize(W)

        total_iterations = 0
        converged = True

        for p in range(n_components):
            w = W[p].copy()

            for iteration in range(self.max_iterations):
                total_iterations += 1

                # Compute w^T * x
                wx = np.dot(w, whitened)

                # Newton update
                # w_new = E{x * g(w^T * x)} - E{g'(w^T * x)} * w
                gwx = g(wx)
                g_prime_wx = g_prime(wx)

                w_new = np.mean(whitened * gwx, axis=1) - np.mean(g_prime_wx) * w

                # Decorrelate from previous components
                for j in range(p):
                    w_new -= np.dot(w_new, W[j]) * W[j]

                # Normalize
                w_new /= np.linalg.norm(w_new) + 1e-10

                # Check convergence
                convergence = min(
                    abs(abs(np.dot(w_new, w)) - 1),
                    abs(abs(np.dot(w_new, -w)) - 1)
                )

                w = w_new

                if convergence < self.tolerance:
                    break
            else:
                converged = False

            W[p] = w

        return W, total_iterations, converged

    def _infomax(
        self,
        whitened: np.ndarray,
        n_components: int,
    ) -> Tuple[np.ndarray, int, bool]:
        """
        Infomax ICA algorithm.

        Args:
            whitened: Whitened data.
            n_components: Number of components.

        Returns:
            Tuple of (unmixing_matrix, iterations, converged).
        """
        n_features, n_samples = whitened.shape

        # Initialize weights
        W = np.eye(n_components, n_features)

        learning_rate = 0.01
        converged = True

        for iteration in range(self.max_iterations):
            # Compute sources
            u = np.dot(W, whitened)

            # Compute nonlinearity (tanh)
            y = np.tanh(u)

            # Update rule
            delta_W = learning_rate * (
                np.eye(n_components) + np.dot((1 - 2 * y), u.T) / n_samples
            ) @ W

            W_new = W + delta_W

            # Check convergence
            change = np.max(np.abs(W_new - W))

            W = W_new

            if change < self.tolerance:
                break
        else:
            converged = False

        return W, iteration + 1, converged

    def _natural_gradient(
        self,
        whitened: np.ndarray,
        n_components: int,
    ) -> Tuple[np.ndarray, int, bool]:
        """
        Natural gradient ICA algorithm.

        Args:
            whitened: Whitened data.
            n_components: Number of components.

        Returns:
            Tuple of (unmixing_matrix, iterations, converged).
        """
        n_features, n_samples = whitened.shape

        # Initialize weights
        W = np.eye(n_components, n_features)

        learning_rate = 0.001
        converged = True

        for iteration in range(self.max_iterations):
            # Compute sources
            u = np.dot(W, whitened)

            # Nonlinearity (tanh derivative approximation)
            phi = np.tanh(u)

            # Natural gradient update
            # dW = (I - phi * u^T) * W
            identity = np.eye(n_components)
            phi_u = np.dot(phi, u.T) / n_samples

            delta_W = learning_rate * np.dot(identity - phi_u, W)

            W_new = W + delta_W

            # Check convergence
            change = np.max(np.abs(W_new - W))

            W = W_new

            if change < self.tolerance:
                break
        else:
            converged = False

        return W, iteration + 1, converged

    def _get_nonlinearity(
        self,
        nonlinearity: NonlinearityType,
    ) -> Tuple[Callable, Callable]:
        """Get nonlinearity function and its derivative."""
        if nonlinearity == NonlinearityType.LOGCOSH:
            g = lambda x: np.tanh(x)
            g_prime = lambda x: 1 - np.tanh(x) ** 2
        elif nonlinearity == NonlinearityType.EXP:
            g = lambda x: x * np.exp(-x ** 2 / 2)
            g_prime = lambda x: (1 - x ** 2) * np.exp(-x ** 2 / 2)
        elif nonlinearity == NonlinearityType.CUBE:
            g = lambda x: x ** 3
            g_prime = lambda x: 3 * x ** 2
        elif nonlinearity == NonlinearityType.TANH:
            g = lambda x: np.tanh(x)
            g_prime = lambda x: 1 - np.tanh(x) ** 2
        else:
            raise ValueError(f"Unknown nonlinearity: {nonlinearity}")

        return g, g_prime

    def _symmetric_orthogonalize(self, W: np.ndarray) -> np.ndarray:
        """Symmetric orthogonalization of matrix W."""
        # W = W * (W^T * W)^(-1/2)
        u, s, vh = linalg.svd(W, full_matrices=False)
        return np.dot(u, vh)

    def reconstruct(
        self,
        ica_result: ICAResult,
        source_indices: Optional[List[int]] = None,
    ) -> np.ndarray:
        """
        Reconstruct signals from selected sources.

        Args:
            ica_result: ICA decomposition result.
            source_indices: Indices of sources to include. None = all.

        Returns:
            Reconstructed signals.
        """
        if source_indices is None:
            sources = ica_result.sources
        else:
            sources = ica_result.sources[source_indices]
            mixing = ica_result.mixing_matrix[:, source_indices]
            return np.dot(mixing, sources) + ica_result.mean[:, np.newaxis]

        return np.dot(ica_result.mixing_matrix, sources) + ica_result.mean[:, np.newaxis]

    def compute_kurtosis(self, sources: np.ndarray) -> np.ndarray:
        """
        Compute kurtosis of sources (measure of non-Gaussianity).

        Args:
            sources: Separated sources.

        Returns:
            Kurtosis values for each source.
        """
        n_sources = sources.shape[0]
        kurtosis = np.zeros(n_sources)

        for i in range(n_sources):
            s = sources[i]
            s = s - np.mean(s)
            s = s / (np.std(s) + 1e-10)
            kurtosis[i] = np.mean(s ** 4) - 3

        return kurtosis

    def sort_sources_by_variance(
        self,
        ica_result: ICAResult,
    ) -> ICAResult:
        """
        Sort sources by their variance (descending).

        Args:
            ica_result: ICA result to sort.

        Returns:
            ICA result with sorted sources.
        """
        variances = np.var(ica_result.sources, axis=1)
        sort_idx = np.argsort(variances)[::-1]

        return ICAResult(
            sources=ica_result.sources[sort_idx],
            mixing_matrix=ica_result.mixing_matrix[:, sort_idx],
            unmixing_matrix=ica_result.unmixing_matrix[sort_idx],
            n_iterations=ica_result.n_iterations,
            converged=ica_result.converged,
            mean=ica_result.mean,
        )
