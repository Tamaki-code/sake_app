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

            // フレーバー値の取得（0-100のレンジを0-1に変換）
            const flavorData = {
                f1: document.getElementById('f1').value / 100,
                f2: document.getElementById('f2').value / 100,
                f3: document.getElementById('f3').value / 100,
                f4: document.getElementById('f4').value / 100,
                f5: document.getElementById('f5').value / 100,
                f6: document.getElementById('f6').value / 100
            };

            try {
                const response = await fetch(`/review/${sakeId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        rating,
                        comment,
                        ...flavorData
                    }),
                });

                if (response.ok) {
                    location.reload();
                } else {
                    const data = await response.json();
                    alert(data.error || 'レビューの投稿中にエラーが発生しました');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('レビューの投稿中にエラーが発生しました');
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