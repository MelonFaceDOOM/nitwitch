//click increase button
//send POST. attempt to increase. no response needed
//increase ambiguity in html by 1 regardless of response
//give increase arrow highlight css "increase-clicked" class
//
//re-click increase button
//send POST, attempt to remove increase
//
//lick decrease button
//send POST. attempt to decrease. no response needed
//decrease ambiguity in html by 1 regardless of response
//give decrease arrow highlight css "decrease-clicked" class
//
//re-click decrease button
//send POST, attempt to remove decrease
//
//increase POST
//take user ip as an arg. check if ip is already in vote table
//if in table and vote == increase, do nothing
//if in table and vote == decrease, remove that and create new entry and increase ambiguity by 1
//if not in table, create new entry in vote table and increase ambiguity by 1
//
//remove increase POST
//if ip in vote table and vote==increase, remove it
//
//decrease in POST
//take user ip as an arg. check if ip is already in vote table
//if in table and vote == decrease, do nothing
//if in table and vote == increase, remove that and create new entry and decrease ambiguity by 1
//if not in table, create new entry in vote table and decrease ambiguity by 1
//
//remove decrease POST
//if ip in vote table and vote==decrease, remove it

// when the page is loaded, find all votes on these images associated with the user and add increase/decrease clicked
// as appropriate

document.addEventListener('DOMContentLoaded', function() {
    const increaseButtons = document.querySelectorAll('.vote-increase');
    const decreaseButtons = document.querySelectorAll('.vote-decrease');


    increaseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const ambiguityObjectId = this.dataset.ambiguityObjectId;
            const ambiguitySpan = this.parentElement.parentElement.querySelector('.ambiguity');
            const ambiguityVoteUrl = button.getAttribute('data-ambiguity-vote-url');
            const sisterButton = this.parentElement.parentElement.querySelector('.vote-decrease')
            if (sisterButton.classList.contains('decrease-clicked')) {
                increaseAmbiguity(ambiguitySpan);
                sisterButton.classList.remove('decrease-clicked');
            }
            if (button.classList.contains('increase-clicked')) {
                decreaseAmbiguity(ambiguitySpan);
                button.classList.remove('increase-clicked');
                sendVote('remove_increase', ambiguityObjectId, ambiguityVoteUrl);
            } else {
                increaseAmbiguity(ambiguitySpan);
                button.classList.add('increase-clicked');
                sendVote('increase', ambiguityObjectId, ambiguityVoteUrl);
            }
        });
    });

    decreaseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const ambiguityObjectId = this.dataset.ambiguityObjectId;
            const ambiguitySpan = this.parentElement.parentElement.querySelector('.ambiguity');
            const ambiguityVoteUrl = button.getAttribute('data-ambiguity-vote-url');
            const sisterButton = this.parentElement.parentElement.querySelector('.vote-increase')
            if (sisterButton.classList.contains('increase-clicked')) {
                decreaseAmbiguity(ambiguitySpan);
                sisterButton.classList.remove('increase-clicked');
            }
            if (button.classList.contains('decrease-clicked')) {
                increaseAmbiguity(ambiguitySpan);
                button.classList.remove('decrease-clicked');
                sendVote('remove_decrease', ambiguityObjectId, ambiguityVoteUrl);
            } else {
                decreaseAmbiguity(ambiguitySpan);
                button.classList.add('decrease-clicked');
                sendVote('decrease', ambiguityObjectId, ambiguityVoteUrl);
            }
        });
    });

    function increaseAmbiguity(ambiguitySpan) {
        ambiguitySpan.textContent = parseInt(ambiguitySpan.textContent) + 1;
    }

    function decreaseAmbiguity(ambiguitySpan) {
        ambiguitySpan.textContent = parseInt(ambiguitySpan.textContent) - 1;
    }

    function sendVote(voteType, ambiguityObjectId, ambiguityVoteUrl) {
//        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const csrfToken = getCookie('csrftoken');
        const formData = new FormData();
        formData.append('vote_type', voteType);
        formData.append('ambiguity_object_id', ambiguityObjectId)
        fetch(ambiguityVoteUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
            },
            body: formData
        });
    }
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}