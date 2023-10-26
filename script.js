const openCalculatorButton = document.getElementById("open-calculator");
const calculatorPopup = document.getElementById("calculator-popup");
const calculateButton = document.getElementById("calculate-button");
const resultDiv = document.getElementById("result");
const closeCalculatorButton = document.getElementById("close-calculator");

openCalculatorButton.addEventListener("click", () => {
  calculatorPopup.style.display = "block";
});

closeCalculatorButton.addEventListener("click", () => {
  calculatorPopup.style.display = "none";
});

calculateButton.addEventListener("click", () => {
});

calculateButton.addEventListener("click", () => {
  const loanableAmount = parseFloat(document.getElementById("loanable-amount").value);
  const amortizationTerms = parseFloat(document.getElementById("amortization-terms").value);

  if (!isNaN(loanableAmount) && !isNaN(amortizationTerms)) {
    const monthlyInterestRate = 0.005518; // Monthly interest rate (5,518.00 / 1000000)
    const numPayments = amortizationTerms * 12;
    
    const monthlyPayment = (loanableAmount * monthlyInterestRate) /
                           (1 - Math.pow(1 + monthlyInterestRate, -numPayments));
    
    resultDiv.textContent = `Monthly Payment: ₱${monthlyPayment.toFixed(2)}`;
  } else {
    resultDiv.textContent = "Please enter valid numbers.";
  }
});

function scrollToVisionMission() {
    const visionMissionSection = document.getElementById('vision-mission');
    visionMissionSection.scrollIntoView({ behavior: 'smooth' });
  }
