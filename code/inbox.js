//TODO: take in a recieved email and process it to inbox
//example used to test initial functionality
const content = {sender:"example@wemail.com", subject:"FREE MONEY!", content:"Click the link to automatically receive $10000000! Just enter your name, card, and SSN!"};
const content2 = {sender:"prof@wemail.com", subject:"your homework", content:"It looks like you haven't yet turned in your assignment. Please turn it in by last Friday, or you will get a 0."};

const emails = [ content, content2 ];

// Select the container div from the HTML
const buttonContainer = document.getElementById('buttonContainer');

// Loop to generate the arbitrary amount of buttons automatically
for (let i = 0; i < emails.length; i++) {
    // 1. Create a new <button> element
    const newButton = document.createElement('button');

    // 2. Set its text content
    let text = ""; 
    for (let j = 0; j < 20; j++) {
        text = text + emails[i].content[j];
    }

    newButton.innerText = "Sender: " + emails[i].sender + ". RE:  " + emails[i].subject + "  -  " + text + "...";

    // 3. Add styling or click behavior
    newButton.style.margin = '5px';

    //Append the new button into the container on the page
    buttonContainer.appendChild(newButton);
    const lineBreak = document.createElement('br');
    buttonContainer.appendChild(lineBreak);
}
