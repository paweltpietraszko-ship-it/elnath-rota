# Repository working agreements

## Owner explanation gate

When delivered code implements behavior that was drafted, inferred, proposed
by a model, or otherwise not yet explicitly accepted by the product owner, do
not issue a PASS/FAIL implementation verdict immediately.

First inspect the exact delivered SHA and explain the result to the owner in
plain Polish, without requiring them to read code or logs. The explanation
must distinguish:

1. behavior already traceable to an explicit owner decision;
2. new user-visible behavior that still needs the owner's acceptance;
3. technical implementation choices that do not change product behavior;
4. behavior added by an agent without owner authority;
5. immediate safety or privacy risks, which must be flagged at once.

For every user-visible part, explain concretely:

- what the program does;
- what triggers it;
- what data it reads, records, sends, retains, or exports;
- what the user sees and can do;
- important failure and recovery behavior.

Then wait for the owner's response. Only after the owner accepts or corrects
the described product behavior may it be frozen as the audit contract and
receive a PASS/FAIL implementation audit.

Do not turn the explanation into additional requirements, and do not treat a
model's earlier proposal as an owner decision. Purely technical details may be
delegated by the owner, but the delegation must be explicit. This gate is not
required for an implementation already covered completely by a frozen owner
contract unless the delivery adds behavior outside that contract.
