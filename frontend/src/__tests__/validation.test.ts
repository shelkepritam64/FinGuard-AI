import { describe, it, expect } from 'vitest';

describe('Transaction Form Validation Logic', () => {
  const validateCreditCard = (values: Record<string, unknown>) => {
    const errors: Record<string, string> = {};
    const numericFields = [
      'distance_from_home',
      'distance_from_last_transaction',
      'ratio_to_median_purchase_price',
    ];
    numericFields.forEach((f) => {
      const val = values[f];
      if (val === undefined || val === '' || isNaN(Number(val)) || Number(val) < 0) {
        errors[f] = 'Must be a non-negative number';
      }
    });

    const binaryFields = ['repeat_retailer', 'used_chip', 'used_pin_number', 'online_order'];
    binaryFields.forEach((f) => {
      const val = Number(values[f]);
      if (val !== 0 && val !== 1) {
        errors[f] = 'Must be 0 (No) or 1 (Yes)';
      }
    });

    return errors;
  };

  const validatePaySim = (values: Record<string, unknown>) => {
    const errors: Record<string, string> = {};
    const stepVal = Number(values.step);
    if (isNaN(stepVal) || stepVal < 1) {
      errors.step = 'Step must be an integer >= 1';
    }

    const amountVal = Number(values.amount);
    if (isNaN(amountVal) || amountVal <= 0) {
      errors.amount = 'Amount must be greater than 0';
    }

    const validTypes = ['CASH_IN', 'CASH_OUT', 'DEBIT', 'PAYMENT', 'TRANSFER'];
    if (!validTypes.includes(String(values.type))) {
      errors.type = 'Select a valid transaction type';
    }

    return errors;
  };

  it('validates legitimate credit card feature inputs', () => {
    const valid = {
      distance_from_home: 4.5,
      distance_from_last_transaction: 0.8,
      ratio_to_median_purchase_price: 1.02,
      repeat_retailer: 1,
      used_chip: 1,
      used_pin_number: 1,
      online_order: 0,
    };
    const errors = validateCreditCard(valid);
    expect(Object.keys(errors).length).toBe(0);
  });

  it('rejects negative distances or invalid binary flags for credit card', () => {
    const invalid = {
      distance_from_home: -5,
      distance_from_last_transaction: 0.8,
      ratio_to_median_purchase_price: 'abc',
      repeat_retailer: 3,
      used_chip: 1,
      used_pin_number: 1,
      online_order: 0,
    };
    const errors = validateCreditCard(invalid);
    expect(errors.distance_from_home).toBe('Must be a non-negative number');
    expect(errors.ratio_to_median_purchase_price).toBe('Must be a non-negative number');
    expect(errors.repeat_retailer).toBe('Must be 0 (No) or 1 (Yes)');
  });

  it('validates correct PaySim transaction inputs', () => {
    const valid = {
      step: 1,
      amount: 1864.28,
      type: 'PAYMENT',
    };
    const errors = validatePaySim(valid);
    expect(Object.keys(errors).length).toBe(0);
  });

  it('rejects invalid PaySim amounts, steps, and types', () => {
    const invalid = {
      step: 0,
      amount: -10,
      type: 'UNKNOWN_TYPE',
    };
    const errors = validatePaySim(invalid);
    expect(errors.step).toBe('Step must be an integer >= 1');
    expect(errors.amount).toBe('Amount must be greater than 0');
    expect(errors.type).toBe('Select a valid transaction type');
  });
});
