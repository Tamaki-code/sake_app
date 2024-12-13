document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Star rating functionality
    const ratingInputs = document.querySelectorAll('.rating-input');
    const ratingStars = document.querySelectorAll('.rating-star');

    ratingStars.forEach((star, index) => {
        star.addEventListener('click', () => {
            const rating = index + 1;
            updateRatingDisplay(rating);
            document.getElementById('rating-value').value = rating;
        });
    });

    function updateRatingDisplay(rating) {
        ratingStars.forEach((star, index) => {
            star.classList.toggle('text-warning', index < rating);
        });
    }

    // Review submission
    const reviewForm = document.getElementById('review-form');
    if (reviewForm) {
        reviewForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const sakeId = reviewForm.dataset.sakeId;
            const rating = document.getElementById('rating-value').value;
            const comment = document.getElementById('review-comment').value;

            try {
                const response = await fetch(`/review/${sakeId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ rating, comment }),
                });

                if (response.ok) {
                    location.reload();
                } else {
                    const data = await response.json();
                    alert(data.error || 'Error submitting review');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error submitting review');
            }
        });
    }

    // Search form
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const query = document.getElementById('search-input').value;
            const flavor = document.getElementById('flavor-select').value;
            window.location.href = `/search?q=${encodeURIComponent(query)}&flavor=${encodeURIComponent(flavor)}`;
        });
    }
});
